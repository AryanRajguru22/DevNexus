"""Measurable non-functional checks that are realistic for the local MVP (see KNOWN_LIMITATIONS.md for the rest)."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import DEV, PM, Api


def test_nfr1_standard_task_is_generated_well_within_60_seconds(api, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    start = time.perf_counter()
    api.post(f"/api/tasks/{tid}/assign")
    elapsed = time.perf_counter() - start
    assert api.get(tid)["status"] == "In Review" and elapsed < 60  # mock provider; a real LLM is not measured here


def test_nfr8_fifty_tasks_in_one_project_all_complete(api, client, setup):
    project, req = setup
    ids = [api.task(project["project_id"], req["req_id"], f"Bulk task {i}")["task_id"] for i in range(50)]
    for tid in ids:
        api.post(f"/api/tasks/{tid}/assign")
    tasks = client.get("/api/tasks", params={"project_id": project["project_id"]}, headers=DEV).json()
    assert len(tasks) == 50 and {t["status"] for t in tasks} == {"In Review"}
    d = client.get("/api/dashboard", params={"project_id": project["project_id"]}, headers=PM).json()
    assert d["totals"]["by_status"]["In Review"] == 50


def test_nfr5_data_survives_an_application_restart(settings):
    first = TestClient(create_app(settings))
    api = Api(first)
    project = api.project()
    req = api.requirement(project["project_id"])
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    api.post(f"/api/tasks/{tid}/assign")
    first.app.state.runtime.engine.dispose()

    second = TestClient(create_app(settings))  # same database file and workspace, new process state
    t = second.get(f"/api/tasks/{tid}", headers=DEV).json()
    assert t["status"] == "In Review" and len(t["history"]) >= 4
    assert len(second.get("/api/users").json()) == 3  # seeding is idempotent
    second.app.state.runtime.engine.dispose()
