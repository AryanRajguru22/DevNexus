"""FR-14, NFR-11, Phase 3 section 14.3: the audit log is append-only and every row has exactly one actor."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app import audit
from app.models import AuditLog, User
from tests.conftest import DEV, PM, advance_to


@pytest.fixture
def db(app):
    with app.state.runtime.session_factory() as session:
        yield session


def seed_entry(db) -> AuditLog:
    entry = audit.record(db, user=db.get(User, 1), action="project.create", target_ref="project:1")
    db.commit()
    return entry


def test_update_is_rejected_by_the_database(db):
    entry = seed_entry(db)
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("UPDATE audit_log SET action='tampered' WHERE log_id=:i"), {"i": entry.log_id})
    db.rollback()
    assert db.get(AuditLog, entry.log_id).action == "project.create"


def test_delete_is_rejected_by_the_database(db):
    entry = seed_entry(db)
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("DELETE FROM audit_log WHERE log_id=:i"), {"i": entry.log_id})
    db.rollback()
    assert db.get(AuditLog, entry.log_id) is not None


def test_orm_level_update_and_delete_are_also_rejected(db):
    entry = seed_entry(db)
    entry.detail = "tampered"
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()
    db.delete(db.get(AuditLog, entry.log_id))
    with pytest.raises(DBAPIError):
        db.commit()


@pytest.mark.parametrize("user_id,agent_id", [(None, None), (1, 1)])
def test_exactly_one_actor_is_enforced_by_a_check_constraint(db, user_id, agent_id):
    db.add(AuditLog(user_id=user_id, agent_id=agent_id, action="x", target_ref="task:1"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_helper_refuses_zero_or_two_actors(db):
    with pytest.raises(ValueError):
        audit.record(db, action="x", target_ref="task:1")


def test_no_endpoint_can_modify_the_audit_trail(client):
    for method in ("put", "patch", "delete", "post"):
        assert getattr(client, method)("/api/audit", headers=PM).status_code in (404, 405)


def test_audit_search_filters_and_ordering(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "Deployed")
    all_rows = client.get("/api/audit", headers=PM).json()
    ids = [r["log_id"] for r in all_rows]
    assert ids == sorted(ids, reverse=True)  # newest first
    by_task = client.get("/api/audit", params={"target_ref": f"task:{tid}"}, headers=PM).json()
    assert by_task and all(r["target_ref"] == f"task:{tid}" for r in by_task)
    assert {r["action"] for r in client.get("/api/audit", params={"agent_id": 1}, headers=PM).json()} == {
        "agent.start", "agent.generate"
    }
    assert all(r["user_id"] == 2 for r in client.get("/api/audit", params={"user_id": 2}, headers=DEV).json())
    assert len(client.get("/api/audit", params={"limit": 2}, headers=PM).json()) == 2
    assert client.get("/api/audit", params={"limit": 0}, headers=PM).status_code == 422
    assert client.get("/api/audit", params={"limit": 501}, headers=PM).status_code == 422


def test_audit_requires_a_known_user(client):
    assert client.get("/api/audit").status_code == 401
