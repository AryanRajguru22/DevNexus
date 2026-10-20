"""PLAN-08 / contract C-3 (proposed E-5): PATCH endpoints for requirements and projects."""
from __future__ import annotations

import pytest

from tests.conftest import DEV, PM


def _audit(client, action: str) -> list[dict]:
    return client.get("/api/audit", params={"action": action}, headers=PM).json()


def _req(client, project_id: int) -> dict:
    return client.get(f"/api/projects/{project_id}/requirements", headers=PM).json()[0]


# ---------- PATCH /api/requirements/{req_id} ----------

def test_pm_edits_a_draft_requirement_and_it_is_audited(client, setup):
    project, req = setup
    r = client.patch(f"/api/requirements/{req['req_id']}", headers=PM,
                     json={"description": "The system shall let students log in.", "priority": "Low", "type": "non-functional"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["description"] == "The system shall let students log in."
    assert body["priority"] == "Low" and body["type"] == "non-functional" and body["status"] == "Draft"
    assert _req(client, project["project_id"]) == body  # persisted
    rows = _audit(client, "requirement.update")
    assert len(rows) == 1 and rows[0]["user_id"] == 1 and rows[0]["target_ref"] == f"requirement:{req['req_id']}"
    assert "description" in rows[0]["detail"] and "priority" in rows[0]["detail"]


def test_draft_requirement_can_be_approved(client, setup):
    _, req = setup
    r = client.patch(f"/api/requirements/{req['req_id']}", headers=PM, json={"status": "Approved"})
    assert r.status_code == 200 and r.json()["status"] == "Approved"


def test_content_change_and_approval_in_one_request(client, setup):
    _, req = setup
    r = client.patch(f"/api/requirements/{req['req_id']}", headers=PM,
                     json={"description": "Final wording of the requirement.", "status": "Approved"})
    assert r.status_code == 200
    assert r.json()["description"] == "Final wording of the requirement." and r.json()["status"] == "Approved"


@pytest.mark.parametrize("change", [
    {"description": "Changed after approval."},
    {"type": "non-functional"},
    {"priority": "Low"},
    {"status": "Draft"},
])
def test_approved_requirement_is_locked(api, client, setup, change):
    project, _ = setup
    approved = api.requirement(project["project_id"], status="Approved")
    r = client.patch(f"/api/requirements/{approved['req_id']}", headers=PM, json=change)
    assert r.status_code == 422 and r.json()["error"]["code"] == "requirement_locked"
    stored = client.get(f"/api/projects/{project['project_id']}/requirements", headers=PM).json()[-1]
    assert stored == approved  # nothing changed
    assert _audit(client, "requirement.update") == []


def test_resending_unchanged_values_to_an_approved_requirement_is_allowed(api, client, setup):
    project, _ = setup
    approved = api.requirement(project["project_id"], status="Approved")
    r = client.patch(f"/api/requirements/{approved['req_id']}", headers=PM,
                     json={"status": "Approved", "priority": approved["priority"]})
    assert r.status_code == 200 and r.json() == approved


def test_developer_cannot_edit_a_requirement_and_denial_is_audited(client, setup):
    _, req = setup
    r = client.patch(f"/api/requirements/{req['req_id']}", headers=DEV, json={"priority": "Low"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    denied = _audit(client, "access.denied")
    assert len(denied) == 1 and denied[0]["target_ref"] == f"endpoint:/api/requirements/{req['req_id']}"


def test_unknown_requirement_is_404(client):
    r = client.patch("/api/requirements/999", headers=PM, json={"priority": "Low"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_requirement_edit_needs_a_known_user(client, setup):
    _, req = setup
    assert client.patch(f"/api/requirements/{req['req_id']}", json={"priority": "Low"}).status_code == 401


@pytest.mark.parametrize("body", [
    {},
    {"description": "abc"},
    {"description": "     "},
    {"description": None},
    {"type": "other"},
    {"priority": "Urgent"},
    {"status": "Rejected"},
    {"project_id": 2},
])
def test_requirement_edit_validation(client, setup, body):
    _, req = setup
    r = client.patch(f"/api/requirements/{req['req_id']}", headers=PM, json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


# ---------- PATCH /api/projects/{project_id} ----------

def test_pm_edits_project_details_and_it_is_audited(client, setup):
    project, _ = setup
    r = client.patch(f"/api/projects/{project['project_id']}", headers=PM,
                     json={"name": "Student Portal v2", "status": "Planning", "objectives": "Ship results first."})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Student Portal v2" and body["status"] == "Planning" and body["objectives"] == "Ship results first."
    assert body["scope"] == project["scope"] and body["pipeline_config"] == project["pipeline_config"]
    assert body["requirement_count"] == 1
    assert client.get(f"/api/projects/{project['project_id']}", headers=DEV).json() == body
    rows = _audit(client, "project.update")
    assert len(rows) == 1 and rows[0]["target_ref"] == f"project:{project['project_id']}"
    assert "name" in rows[0]["detail"] and "status" in rows[0]["detail"]


def test_end_date_is_checked_against_the_stored_start_date(api, client):
    project = api.project(start_date="2026-10-10", end_date="2026-11-30")
    r = client.patch(f"/api/projects/{project['project_id']}", headers=PM, json={"end_date": "2026-10-01"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert client.get(f"/api/projects/{project['project_id']}", headers=PM).json()["end_date"] == "2026-11-30"


def test_dates_in_the_body_must_be_ordered(client, setup):
    project, _ = setup
    r = client.patch(f"/api/projects/{project['project_id']}", headers=PM,
                     json={"start_date": "2026-12-01", "end_date": "2026-11-01"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_dates_can_be_cleared_with_null(api, client):
    project = api.project(start_date="2026-10-10", end_date="2026-11-30")
    r = client.patch(f"/api/projects/{project['project_id']}", headers=PM, json={"end_date": None})
    assert r.status_code == 200 and r.json()["end_date"] is None and r.json()["start_date"] == "2026-10-10"


def test_developer_cannot_edit_a_project_and_denial_is_audited(client, setup):
    project, _ = setup
    r = client.patch(f"/api/projects/{project['project_id']}", headers=DEV, json={"name": "Hijacked"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert len(_audit(client, "access.denied")) == 1
    assert client.get(f"/api/projects/{project['project_id']}", headers=PM).json()["name"] == project["name"]


def test_unknown_project_edit_is_404(client):
    r = client.patch("/api/projects/999", headers=PM, json={"name": "Nope"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("body", [
    {},
    {"name": ""},
    {"name": "   "},
    {"name": None},
    {"scope": "x" * 2001},
    {"status": "Archived"},
    {"start_date": "not-a-date"},
    {"pipeline_config": {"retry_limit": 5}},
    {"manager_id": 2},
])
def test_project_edit_validation(client, setup, body):
    project, _ = setup
    r = client.patch(f"/api/projects/{project['project_id']}", headers=PM, json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert client.get(f"/api/projects/{project['project_id']}", headers=PM).json() == project | {"requirement_count": 1}
