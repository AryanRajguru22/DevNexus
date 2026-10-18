"""FR-1, FR-2, FR-3: projects, requirements, pipeline configuration; identity and role checks (NFR-3)."""
from __future__ import annotations

import pytest

from tests.conftest import DEV, PM, as_user

PROJECT = {
    "name": "Student Portal",
    "problem_statement": "Students cannot see results online.",
    "scope": "Login and results view.",
    "objectives": "Deliver a working login API.",
}


def test_health_needs_no_user(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_users_list_feeds_the_user_switcher(client):
    users = client.get("/api/users").json()
    assert [(u["role"]) for u in users] == ["project_manager", "developer", "developer"]


@pytest.mark.parametrize("headers", [{}, {"X-User-Id": "abc"}, {"X-User-Id": "999"}])
def test_missing_or_unknown_user_is_401(client, headers):
    r = client.get("/api/projects", headers=headers)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_authenticated"


def test_pm_creates_project_with_default_pipeline(client):  # FR-1
    r = client.post("/api/projects", json=PROJECT | {"start_date": "2026-10-01", "end_date": "2026-11-01"}, headers=PM)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Student Portal" and body["manager_id"] == 1 and body["status"] == "Active"
    assert body["problem_statement"] and body["scope"] and body["objectives"]
    assert body["pipeline_config"]["active_agents"] == ["code_generation", "testing", "deployment"]
    assert body["pipeline_config"]["retry_limit"] == 2
    assert client.get(f"/api/projects/{body['project_id']}", headers=DEV).json()["name"] == "Student Portal"
    assert len(client.get("/api/projects", headers=DEV).json()) == 1


def test_developer_cannot_create_project_and_denial_is_audited(client):
    r = client.post("/api/projects", json=PROJECT, headers=DEV)
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    denied = client.get("/api/audit", params={"action": "access.denied"}, headers=PM).json()
    assert len(denied) == 1 and denied[0]["user_id"] == 2 and "/api/projects" in denied[0]["target_ref"]


@pytest.mark.parametrize(
    "override",
    [
        {"name": ""},
        {"name": "   "},
        {"problem_statement": ""},
        {"scope": "x" * 2001},
        {"objectives": ""},
        {"start_date": "2026-12-01", "end_date": "2026-11-01"},
        {"start_date": "not-a-date"},
    ],
)
def test_project_validation(client, override):
    r = client.post("/api/projects", json=PROJECT | override, headers=PM)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert client.get("/api/projects", headers=PM).json() == []  # nothing persisted


def test_unknown_project_is_404(client):
    r = client.get("/api/projects/42", headers=PM)
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_requirements_capture_functional_and_non_functional(api, client):  # FR-2
    pid = api.project()["project_id"]
    api.requirement(pid, type="functional", priority="High")
    api.requirement(pid, type="non-functional", priority="Low", description="Pages shall load within 2 seconds.")
    reqs = client.get(f"/api/projects/{pid}/requirements", headers=DEV).json()
    assert [r["type"] for r in reqs] == ["functional", "non-functional"]
    assert client.get(f"/api/projects/{pid}", headers=DEV).json()["requirement_count"] == 2


@pytest.mark.parametrize(
    "override",
    [
        {"description": ""},
        {"description": "abc"},
        {"description": "    ab    "},
        {"type": "business"},
        {"priority": "Urgent"},
        {"status": "Done"},
    ],
)
def test_requirement_validation(api, client, override):
    pid = api.project()["project_id"]
    body = {"description": "The system shall do something.", "type": "functional", "priority": "High"} | override
    assert client.post(f"/api/projects/{pid}/requirements", json=body, headers=PM).status_code == 422


def test_requirement_for_unknown_project_and_wrong_role(api, client):
    body = {"description": "The system shall do something.", "type": "functional", "priority": "High"}
    assert client.post("/api/projects/9/requirements", json=body, headers=PM).status_code == 404
    pid = api.project()["project_id"]
    assert client.post(f"/api/projects/{pid}/requirements", json=body, headers=DEV).status_code == 403


def test_pipeline_configuration_is_stored_and_audited(api, client):  # FR-3
    pid = api.project()["project_id"]
    cfg = {
        "active_agents": ["code_generation", "testing"],
        "retry_limit": 4,
        "constraints": {"max_loc": 120, "target_environment": "production", "delay_threshold_hours": 24},
    }
    r = client.put(f"/api/projects/{pid}/pipeline", json=cfg, headers=PM)
    assert r.status_code == 200 and r.json()["pipeline_config"] == cfg
    assert client.get(f"/api/projects/{pid}", headers=DEV).json()["pipeline_config"] == cfg
    assert client.get("/api/audit", params={"action": "pipeline.configure"}, headers=PM).json()


@pytest.mark.parametrize(
    "cfg",
    [
        {"active_agents": ["code_generation", "wizard"], "retry_limit": 2},
        {"active_agents": ["testing", "testing"], "retry_limit": 2},
        {"active_agents": [], "retry_limit": -1},
        {"active_agents": [], "retry_limit": 11},
        {"active_agents": [], "retry_limit": 2, "constraints": {"max_loc": 5}},
        {"active_agents": [], "retry_limit": 2, "constraints": {"max_loc": 99999}},
        {"active_agents": [], "retry_limit": 2, "constraints": {"target_environment": "moon"}},
        {"active_agents": [], "retry_limit": 2, "constraints": {"delay_threshold_hours": 0}},
    ],
)
def test_pipeline_validation(api, client, cfg):
    pid = api.project()["project_id"]
    before = client.get(f"/api/projects/{pid}", headers=PM).json()["pipeline_config"]
    r = client.put(f"/api/projects/{pid}/pipeline", json=cfg, headers=PM)
    assert r.status_code == 422
    assert client.get(f"/api/projects/{pid}", headers=PM).json()["pipeline_config"] == before


def test_developer_cannot_configure_pipeline(api, client):
    pid = api.project()["project_id"]
    r = client.put(f"/api/projects/{pid}/pipeline", json={"active_agents": [], "retry_limit": 1}, headers=DEV)
    assert r.status_code == 403


def test_error_envelope_for_unknown_route(client):
    r = client.get("/api/nope", headers=PM)
    assert r.status_code == 404 and set(r.json()["error"]) == {"code", "message", "details"}


def test_second_pm_identity_comes_from_the_database_not_the_client(client):
    r = client.get("/api/me", headers=as_user(3))
    assert r.json()["role"] == "developer"
