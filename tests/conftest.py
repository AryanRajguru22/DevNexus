"""Shared fixtures: every test gets its own temporary SQLite file and Git workspace (no shared state)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

PM_ID, DEV1_ID, DEV2_ID = 1, 2, 3  # seeded demo users: Aryan (PM), Member C (Dev), Member B (Dev)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path, database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}")


@pytest.fixture
def app(settings):
    application = create_app(settings)
    yield application
    application.state.runtime.engine.dispose()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def as_user(user_id: int) -> dict[str, str]:
    return {"X-User-Id": str(user_id)}


PM = as_user(PM_ID)
DEV = as_user(DEV1_ID)
DEV2 = as_user(DEV2_ID)


class Api:
    """Thin helper for building scenarios through the real HTTP API."""

    def __init__(self, client: TestClient):
        self.c = client

    def project(self, **overrides) -> dict:
        body = {
            "name": "Student Portal",
            "problem_statement": "Students cannot see results online.",
            "scope": "Login and results view.",
            "objectives": "Deliver a working login API.",
        } | overrides
        r = self.c.post("/api/projects", json=body, headers=PM)
        assert r.status_code == 201, r.text
        return r.json()

    def requirement(self, project_id: int, **overrides) -> dict:
        body = {"description": "The system shall allow users to log in.", "type": "functional", "priority": "High"} | overrides
        r = self.c.post(f"/api/projects/{project_id}/requirements", json=body, headers=PM)
        assert r.status_code == 201, r.text
        return r.json()

    def pipeline(self, project_id: int, **overrides) -> dict:
        body = {"active_agents": ["code_generation", "testing", "deployment"], "retry_limit": 2} | overrides
        r = self.c.put(f"/api/projects/{project_id}/pipeline", json=body, headers=PM)
        assert r.status_code == 200, r.text
        return r.json()

    def task(self, project_id: int, req_id: int, title: str = "Build login API", **overrides) -> dict:
        body = {"project_id": project_id, "req_id": req_id, "title": title} | overrides
        r = self.c.post("/api/tasks", json=body, headers=DEV)
        assert r.status_code == 201, r.text
        return r.json()

    def get(self, task_id: int, headers=DEV) -> dict:
        r = self.c.get(f"/api/tasks/{task_id}", headers=headers)
        assert r.status_code == 200, r.text
        return r.json()

    def post(self, path: str, headers=DEV, json=None, expected: int = 200):
        r = self.c.post(path, headers=headers, json=json)
        assert r.status_code == expected, f"{path}: {r.status_code} {r.text}"
        return r.json()


@pytest.fixture
def api(client) -> Api:
    return Api(client)


@pytest.fixture
def setup(api):
    """A project with one requirement; returns (project, requirement)."""
    project = api.project()
    req = api.requirement(project["project_id"])
    return project, req


def advance_to(api: Api, task_id: int, status: str) -> dict:
    """Drive a Created task through the real workflow until it reaches `status` (agents run synchronously
    in the TestClient, so each call lands in its next resting state)."""
    order = ["Created", "In Review", "Ready for Deployment", "Deployed"]
    assert status in order
    if status == "Created":
        return api.get(task_id)
    api.post(f"/api/tasks/{task_id}/assign")
    if status == "In Review":
        return api.get(task_id)
    api.post(f"/api/tasks/{task_id}/approve")
    if status == "Ready for Deployment":
        return api.get(task_id)
    api.post(f"/api/tasks/{task_id}/deploy")
    return api.get(task_id)
