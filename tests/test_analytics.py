"""FR-10, FR-11, FR-12: estimation, risk and dashboard. Figures must come from persisted data and the Phase 2 formulas."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.models import Project, RiskReport, Task, utcnow
from app.services import analytics
from tests.conftest import DEV, PM, advance_to


@pytest.fixture
def db(app):
    with app.state.runtime.session_factory() as session:
        yield session


# -- Phase 2 constants ---------------------------------------------------------------------------------------------
def test_cocomo_reproduces_the_phase2_numbers():
    effort, duration, team = analytics.basic_cocomo(8.0)  # 8,000 LOC (Phase 2 section 3)
    assert round(effort, 1) == 21.3  # Phase 2 section 5
    assert round(duration, 1) == 8.0  # Phase 2 section 6
    assert round(team, 1) == 2.7
    assert 1_270_000 < effort * analytics.COST_PER_PERSON_MONTH_INR < 1_290_000  # about Rs 12,78,000 (section 7)
    assert analytics.basic_cocomo(0) == (0.0, 0.0, 0.0)


@pytest.mark.parametrize(
    "score,level", [(0, "Low"), (8, "Low"), (9, "Medium"), (14, "Medium"), (15, "High"), (25, "High")]
)
def test_risk_level_thresholds_from_phase2(score, level):
    assert analytics.level_for(score) == level


# -- estimation (FR-10) ----------------------------------------------------------------------------------------------
def test_estimation_with_no_tasks_is_zero(api, client):
    pid = api.project()["project_id"]
    est = client.get("/api/reports/estimation", params={"project_id": pid}, headers=PM).json()
    assert est["task_count"] == 0 and est["effort_person_months"] == 0 and est["cost_inr"] == 0
    assert est["phase2_baseline"]["effort_person_months"] == 21.3


def test_estimation_uses_planned_size_then_actual_generated_size(api, client, setup):
    project, req = setup
    pid = project["project_id"]
    tid = api.task(pid, req["req_id"])["task_id"]
    est = client.get("/api/reports/estimation", params={"project_id": pid}, headers=PM).json()
    assert est["loc_planned"] == 100 and est["loc_actual"] == 0  # max_loc 200 // 2
    expected_effort = 2.4 * (0.1**1.05)
    assert est["effort_person_months"] == round(expected_effort, 2)
    assert est["cost_inr"] == round(expected_effort * 60000, 2)

    advance_to(api, tid, "In Review")
    est = client.get("/api/reports/estimation", params={"project_id": pid}, headers=PM).json()
    assert est["loc_planned"] == 0 and 15 <= est["loc_actual"] <= 30  # real generated lines
    assert est["kloc"] == round(est["loc_total"] / 1000, 3)
    effort = 2.4 * (est["loc_total"] / 1000) ** 1.05
    assert est["effort_person_months"] == round(effort, 2)
    assert est["duration_months"] == round(2.5 * effort**0.38, 2)  # from the unrounded effort
    assert est["team_size"] == round(effort / (2.5 * effort**0.38), 2)


def test_estimation_all_projects_and_unknown_project(api, client, setup):
    project, req = setup
    api.task(project["project_id"], req["req_id"])
    assert client.get("/api/reports/estimation", headers=PM).json()["task_count"] == 1
    assert client.get("/api/reports/estimation", params={"project_id": 99}, headers=PM).status_code == 404


# -- dashboard (FR-12) -----------------------------------------------------------------------------------------------
def test_empty_dashboard_has_no_invented_numbers(api, client):
    pid = api.project()["project_id"]
    d = client.get("/api/dashboard", params={"project_id": pid}, headers=PM).json()
    assert d["totals"]["tasks"] == 0 and d["progress_pct"] == 0.0
    assert d["coverage"]["average_pct"] is None and d["coverage"]["simulated"] is True
    assert set(d["totals"]["by_status"]) == {
        "Created", "Assigned", "Generating", "In Review", "Testing", "Ready for Deployment", "Deployed", "Failed"
    }
    assert [v["deployed"] for v in d["velocity"]] == [0, 0, 0, 0] and d["risk"]["level"] == "Low"
    assert d["latest_risk_report"] is None


def test_dashboard_reflects_task_states_progress_velocity_and_coverage(api, client, setup):
    project, req = setup
    pid, rid = project["project_id"], req["req_id"]
    done = api.task(pid, rid, "Task done")["task_id"]
    review = api.task(pid, rid, "Task review")["task_id"]
    api.task(pid, rid, "Task new")
    failed = api.task(pid, rid, "Task failing [fail-llm]")["task_id"]
    advance_to(api, done, "Deployed")
    advance_to(api, review, "In Review")
    api.post(f"/api/tasks/{failed}/assign")
    d = client.get("/api/dashboard", params={"project_id": pid}, headers=DEV).json()
    assert d["totals"]["tasks"] == 4
    assert d["totals"]["by_status"]["Deployed"] == 1 and d["totals"]["by_status"]["In Review"] == 1
    assert d["totals"]["by_status"]["Created"] == 1 and d["totals"]["by_status"]["Failed"] == 1
    assert d["totals"]["by_group"] == {"queued": 1, "in_progress": 1, "completed": 1, "failed": 1}
    assert d["progress_pct"] == 25.0
    assert d["velocity"][-1]["deployed"] == 1  # current sprint window
    assert d["coverage"]["average_pct"] == 100.0 and d["coverage"]["tasks_with_results"] == 1
    # all-projects dashboard agrees
    assert client.get("/api/dashboard", headers=PM).json()["totals"]["tasks"] == 4
    assert client.get("/api/dashboard", params={"project_id": 99}, headers=PM).status_code == 404


def test_dashboard_is_fast_with_50_tasks(api, client, setup):  # NFR-2 (5 seconds)
    import time

    project, req = setup
    for i in range(50):
        api.task(project["project_id"], req["req_id"], f"Task number {i}")
    start = time.perf_counter()
    assert client.get("/api/dashboard", params={"project_id": project["project_id"]}, headers=PM).status_code == 200
    assert time.perf_counter() - start < 5


# -- risk (FR-11) ----------------------------------------------------------------------------------------------------
def test_delayed_tasks_are_flagged_after_the_threshold(api, db, setup):
    project, req = setup
    pid = project["project_id"]
    for i in range(4):
        api.task(pid, req["req_id"], f"Idle task {i}")
    fresh = analytics.assess_risk(db, pid, now=utcnow())
    assert fresh["items"] == [] and fresh["level"] == "Low"
    later = utcnow() + timedelta(hours=73)  # default threshold is 72 h
    risk = analytics.assess_risk(db, pid, now=later)
    item = risk["items"][0]
    assert item["category"] == "delayed_tasks" and len(item["task_ids"]) == 4
    assert (item["probability"], item["impact"], item["score"], item["level"]) == (5, 3, 15, "High")
    assert risk["level"] == "High" and risk["score"] == 15


def test_deployed_tasks_are_never_delayed(api, db, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "Deployed")
    assert analytics.assess_risk(db, project["project_id"], now=utcnow() + timedelta(days=30))["items"] == []


def test_schedule_slippage_after_end_date_and_by_progress_gap(api, db, setup):
    project, req = setup
    pid = project["project_id"]
    api.task(pid, req["req_id"])
    row = db.get(Project, pid)
    row.start_date, row.end_date = date(2026, 1, 1), date(2026, 1, 31)
    db.commit()
    overdue = analytics.assess_risk(db, pid, now=datetime(2026, 2, 15))
    slip = next(i for i in overdue["items"] if i["category"] == "schedule_slippage")
    assert (slip["probability"], slip["score"], slip["level"]) == (5, 20, "High")
    behind = analytics.assess_risk(db, pid, now=datetime(2026, 1, 21))  # 2/3 elapsed, 0% progress
    slip = next(i for i in behind["items"] if i["category"] == "schedule_slippage")
    assert slip["probability"] == 4 and slip["level"] == "High"  # 1 + round(0.667 * 5) = 4 -> 4 * 4 = 16
    on_track = analytics.assess_risk(db, pid, now=datetime(2026, 1, 3))
    assert not [i for i in on_track["items"] if i["category"] == "schedule_slippage"]


def test_risk_threshold_stores_one_report_and_notifies_the_pm_once(api, client, db, setup):
    project, req = setup
    pid = project["project_id"]
    api.task(pid, req["req_id"])
    row = db.get(Project, pid)
    row.start_date, row.end_date = date(2025, 1, 1), date(2025, 1, 31)  # long overdue
    db.commit()
    assert analytics.check_risk_threshold(db, row) is not None
    db.commit()
    assert analytics.check_risk_threshold(db, row) is None  # already High: no duplicate report/notification
    db.commit()
    assert db.query(RiskReport).count() == 1
    notes = [n for n in client.get("/api/notifications", headers=PM).json() if n["kind"] == "risk_threshold"]
    assert len(notes) == 1 and "High" in notes[0]["message"]


def test_risk_report_endpoints(api, client, setup):
    project, req = setup
    pid = project["project_id"]
    assert client.get("/api/reports/risk", params={"project_id": pid}, headers=PM).status_code == 404
    assert client.post("/api/reports/risk", params={"project_id": pid}, headers=DEV).status_code == 403
    created = client.post("/api/reports/risk", params={"project_id": pid}, headers=PM)
    assert created.status_code == 201 and created.json()["risk_level"] == "Low"
    latest = client.get("/api/reports/risk", params={"project_id": pid}, headers=DEV).json()
    assert latest["report_id"] == created.json()["report_id"] and latest["details"]["items"] == []
    assert client.get("/api/audit", params={"action": "risk_report.generate"}, headers=PM).json()
    assert client.get("/api/reports/risk", headers=PM).status_code == 422  # project_id required
    d = client.get("/api/dashboard", params={"project_id": pid}, headers=PM).json()
    assert d["latest_risk_report"]["report_id"] == latest["report_id"]


def test_repeated_failures_category_and_probability_scale(api, client, db, setup):
    project, req = setup
    pid = project["project_id"]
    ids = []
    for i in range(3):
        tid = api.task(pid, req["req_id"], f"Always failing {i} [fail-llm-always]")["task_id"]
        api.post(f"/api/tasks/{tid}/assign")
        api.post(f"/api/tasks/{tid}/retry")  # 2 failed runs each
        ids.append(tid)
    risk = analytics.assess_risk(db, pid)
    item = next(i for i in risk["items"] if i["category"] == "repeated_failures")
    assert sorted(item["task_ids"]) == sorted(ids)
    assert (item["probability"], item["impact"], item["score"]) == (4, 4, 16) and risk["level"] == "High"
    assert any(n["kind"] == "risk_threshold" for n in client.get("/api/notifications", headers=PM).json())
