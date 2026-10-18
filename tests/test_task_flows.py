"""FR-4..FR-9, FR-13, FR-14: the supervised task pipeline through the real HTTP API.

The TestClient runs background agent jobs before returning, so each call lands in its next resting state.
"""
from __future__ import annotations

import pytest

from tests.conftest import DEV, DEV2, PM, advance_to


def history_actions(task: dict) -> list[str]:
    return [h["action"] for h in task["history"]]


def notifications(client, headers) -> list[dict]:
    return client.get("/api/notifications", headers=headers).json()


# -- happy path ---------------------------------------------------------------------------------------------------
def test_happy_path_review_test_deploy(api, client, setup, app):
    project, req = setup
    task = api.task(project["project_id"], req["req_id"], description="Return a token for valid credentials.")
    tid = task["task_id"]
    assert task["status"] == "Created" and task["status_group"] == "queued" and task["developer_id"] == 2

    assigned = api.post(f"/api/tasks/{tid}/assign")
    assert assigned["status"] == "Assigned"
    t = api.get(tid)
    assert t["status"] == "In Review" and t["status_group"] == "in_progress"  # FR-5: code generated
    assert len(t["runs"]) == 1 and t["runs"][0]["status"] == "completed"
    branch = t["runs"][0]["branch_name"]
    assert branch.startswith("feature/task-") and branch not in ("main", "master")  # NFR-6

    diff = client.get(f"/api/tasks/{tid}/diff", headers=DEV).json()  # FR-7: review shows the diff against main
    assert diff["branch"] == branch and diff["base"] == "main"
    assert diff["files"][0]["path"].startswith("generated/") and "+def handle_" in diff["files"][0]["diff"]
    assert app.state.runtime.git.read_main(project["project_id"]) == {}  # nothing merged before approval

    api.post(f"/api/tasks/{tid}/approve", json={"comments": "looks good"})
    t = api.get(tid)
    assert t["status"] == "Ready for Deployment"  # FR-8: tests ran automatically after approval
    assert t["test_results"][0]["failed_count"] == 0 and t["test_results"][0]["simulated"] is True
    assert app.state.runtime.git.read_main(project["project_id"]) == {}  # still not merged

    out = api.post(f"/api/tasks/{tid}/deploy", json={"environment": "staging"})  # FR-9
    assert out["outcome"] == "succeeded" and out["task"]["status"] == "Deployed"
    t = api.get(tid)
    assert t["status"] == "Deployed" and t["status_group"] == "completed"
    assert t["deployments"][0]["status"] == "succeeded" and t["deployments"][0]["environment"] == "staging"
    assert any(p.startswith("generated/") for p in app.state.runtime.git.read_main(project["project_id"]))

    # FR-14: attributable audit trail of agent actions and human approvals, in order, with exactly one actor each
    assert history_actions(t) == [
        "task.create", "task.assign", "agent.start", "agent.generate", "task.approve", "agent.test",
        "task.deploy_authorise", "agent.deploy",
    ]
    approve = next(h for h in t["history"] if h["action"] == "task.approve")
    assert approve["user_id"] == 2 and approve["agent_id"] is None and approve["detail"] == "looks good"  # NFR-11
    assert next(h for h in t["history"] if h["action"] == "agent.generate")["actor_name"] == "Code Generation Agent"


def test_notifications_reach_the_right_users(api, client, setup):  # FR-13
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "Deployed")
    dev_kinds = [n["kind"] for n in notifications(client, DEV)]
    pm_kinds = [n["kind"] for n in notifications(client, PM)]
    assert sorted(dev_kinds) == ["code_ready", "deployment_completed", "tests_passed"]
    assert pm_kinds == ["deployment_completed"]
    assert notifications(client, DEV2) == []  # another developer sees nothing

    n = notifications(client, DEV)[0]
    assert client.post(f"/api/notifications/{n['notification_id']}/read", headers=DEV).json()["is_read"] is True
    assert len(client.get("/api/notifications", params={"unread_only": True}, headers=DEV).json()) == 2
    assert client.post(f"/api/notifications/{n['notification_id']}/read", headers=PM).status_code == 404


# -- creation and assignment --------------------------------------------------------------------------------------
def test_task_creation_rules(api, client, setup):
    project, req = setup
    pid, rid = project["project_id"], req["req_id"]
    other = api.project(name="Other")
    other_req = api.requirement(other["project_id"])

    r = client.post("/api/tasks", json={"project_id": pid, "req_id": rid, "title": "x"}, headers=DEV)
    assert r.status_code == 422  # title too short
    r = client.post("/api/tasks", json={"project_id": pid, "req_id": other_req["req_id"], "title": "Valid title"}, headers=DEV)
    assert r.status_code == 422 and r.json()["error"]["code"] == "requirement_project_mismatch"
    assert client.post("/api/tasks", json={"project_id": pid, "req_id": 999, "title": "Valid title"}, headers=DEV).status_code == 404
    assert client.post("/api/tasks", json={"project_id": 999, "req_id": rid, "title": "Valid title"}, headers=DEV).status_code == 404
    assert client.post("/api/tasks", json={"project_id": pid, "req_id": rid, "title": "Valid title"}, headers=PM).status_code == 403
    assert client.get("/api/tasks", headers=DEV).json() == []


def test_task_listing_filters(api, client, setup):
    project, req = setup
    pid, rid = project["project_id"], req["req_id"]
    a, b = api.task(pid, rid, "Task A"), api.task(pid, rid, "Task B")
    advance_to(api, b["task_id"], "In Review")
    assert len(client.get("/api/tasks", params={"project_id": pid}, headers=PM).json()) == 2
    assert [t["task_id"] for t in client.get("/api/tasks", params={"status": "In Review"}, headers=PM).json()] == [b["task_id"]]
    assert [t["task_id"] for t in client.get("/api/tasks", params={"status_group": "queued"}, headers=PM).json()] == [a["task_id"]]
    assert client.get("/api/tasks", params={"status": "Bogus"}, headers=PM).status_code == 422


def test_only_the_code_generation_agent_can_be_assigned(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    r = client.post(f"/api/tasks/{tid}/assign", json={"agent_type": "testing"}, headers=DEV)
    assert r.status_code == 422 and r.json()["error"]["code"] == "agent_not_assignable"
    assert api.get(tid)["status"] == "Created"


def test_assignment_refused_when_agent_not_active_in_pipeline(api, client, setup):  # UC-03 alt 3a
    project, req = setup
    api.pipeline(project["project_id"], active_agents=["testing", "deployment"])
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    r = client.post(f"/api/tasks/{tid}/assign", headers=DEV)
    assert r.status_code == 409 and r.json()["error"]["code"] == "agent_inactive"
    assert api.get(tid)["status"] == "Created"


def test_pm_cannot_assign_review_or_retry(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    for action in ("assign", "approve", "reject", "retry", "tests"):
        assert client.post(f"/api/tasks/{tid}/{action}", json={"comments": "x"}, headers=PM).status_code == 403
    assert api.get(tid)["status"] == "Created"


@pytest.mark.parametrize("action", ["approve", "reject", "retry", "tests", "deploy"])
def test_actions_in_the_wrong_state_are_409(api, client, setup, action):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]  # Created
    r = client.post(f"/api/tasks/{tid}/{action}", json={"comments": "x"}, headers=DEV)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition"
    assert api.get(tid)["status"] == "Created"


def test_cannot_assign_twice(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "In Review")
    assert client.post(f"/api/tasks/{tid}/assign", headers=DEV).status_code == 409


def test_unknown_task_is_404(client):
    assert client.get("/api/tasks/77", headers=DEV).status_code == 404
    assert client.post("/api/tasks/77/approve", headers=DEV).status_code == 404


# -- review gate (FR-7) -------------------------------------------------------------------------------------------
def test_reject_sends_task_back_for_rework_with_feedback(api, client, setup, app):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "In Review")
    rejected = api.post(f"/api/tasks/{tid}/reject", json={"comments": "add input validation"})
    assert rejected["status"] == "Generating"
    t = api.get(tid)
    assert t["status"] == "In Review" and len(t["runs"]) == 2  # a new agent run per rework
    code = next(iter(app.state.runtime.git.read_branch(project["project_id"], t["runs"][1]["branch_name"]).values()))
    assert "add input validation" in code and "attempt 2" in code
    rej = next(h for h in t["history"] if h["action"] == "task.reject")
    assert rej["detail"] == "add input validation" and rej["user_id"] == 2


@pytest.mark.parametrize("body", [{}, {"comments": ""}, {"comments": "   "}])
def test_reject_requires_comments(api, client, setup, body):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "In Review")
    assert client.post(f"/api/tasks/{tid}/reject", json=body, headers=DEV).status_code == 422
    assert api.get(tid)["status"] == "In Review"


def test_nothing_reaches_main_without_approval_and_deployment(api, setup, app):  # FR-7, FR-9
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "Ready for Deployment")
    assert app.state.runtime.git.read_main(project["project_id"]) == {}


def test_rework_is_bounded_by_retry_limit_and_reported_as_risk(api, client, setup):
    project, req = setup
    pid = project["project_id"]
    api.pipeline(pid, retry_limit=1)
    tid = api.task(pid, req["req_id"])["task_id"]
    advance_to(api, tid, "In Review")
    api.post(f"/api/tasks/{tid}/reject", json={"comments": "again"})  # rework 1 of 1 allowed
    assert api.get(tid)["status"] == "In Review"
    r = client.post(f"/api/tasks/{tid}/reject", json={"comments": "and again"}, headers=DEV)
    assert r.status_code == 409 and r.json()["error"]["code"] == "retry_limit_exceeded"
    t = api.get(tid)
    assert t["status"] == "In Review" and t["rework_allowed"] is False and len(t["runs"]) == 2  # no new state, no new run
    assert "task.retry_limit_exceeded" in history_actions(t)
    assert "approve" in t["allowed_actions"] and "reject" not in t["allowed_actions"]
    assert any(n["kind"] == "risk_threshold" for n in notifications(client, PM))  # FR-13
    risk = client.get("/api/dashboard", params={"project_id": pid}, headers=PM).json()["risk"]
    assert any(i["category"] == "repeated_failures" and tid in i["task_ids"] for i in risk["items"])  # FR-11


# -- automated tests gate (FR-8) ----------------------------------------------------------------------------------
def test_failing_tests_send_the_task_back_to_generation_then_pass(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"], "Build login API [fail-tests]")["task_id"]
    advance_to(api, tid, "In Review")
    api.post(f"/api/tasks/{tid}/approve")
    t = api.get(tid)
    # first test run failed -> rework (second generation run) -> back in review, awaiting a new decision
    assert t["status"] == "In Review" and len(t["runs"]) == 2
    assert t["test_results"][0]["failed_count"] == 1 and "tests_failed" in [n["kind"] for n in notifications(client, DEV)]
    api.post(f"/api/tasks/{tid}/approve")
    t = api.get(tid)
    assert t["status"] == "Ready for Deployment" and t["test_results"][1]["failed_count"] == 0
    assert t["test_results"][1]["run_id"] == t["runs"][1]["run_id"]  # results hang off the run that produced the code


def test_persistent_test_failure_stays_in_testing_at_the_limit_and_can_be_rerun(api, client, setup):
    project, req = setup
    pid = project["project_id"]
    api.pipeline(pid, retry_limit=0)
    tid = api.task(pid, req["req_id"], "Build login API [fail-tests-always]")["task_id"]
    advance_to(api, tid, "In Review")
    api.post(f"/api/tasks/{tid}/approve")
    t = api.get(tid)
    assert t["status"] == "Testing" and t["test_results"][0]["failed_count"] > 0
    assert "task.retry_limit_exceeded" in history_actions(t) and t["allowed_actions"] == ["tests"]
    assert any(n["kind"] == "risk_threshold" for n in notifications(client, PM))
    api.post(f"/api/tasks/{tid}/tests")  # re-run (UC-06): still failing, still Testing, history grows
    t = api.get(tid)
    assert t["status"] == "Testing" and len(t["test_results"]) == 2 and "task.tests_rerun" in history_actions(t)


def test_testing_agent_inactive_blocks_approval(api, client, setup):
    project, req = setup
    api.pipeline(project["project_id"], active_agents=["code_generation", "deployment"])
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "In Review")
    r = client.post(f"/api/tasks/{tid}/approve", headers=DEV)
    assert r.status_code == 409 and r.json()["error"]["code"] == "agent_inactive"
    assert api.get(tid)["status"] == "In Review"


# -- failures and retry -------------------------------------------------------------------------------------------
def test_llm_outage_fails_the_task_then_retry_succeeds(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"], "Build login API [fail-llm]")["task_id"]
    api.post(f"/api/tasks/{tid}/assign")
    t = api.get(tid)
    assert t["status"] == "Failed" and t["status_group"] == "failed"
    assert t["runs"][0]["status"] == "failed" and "outage" in t["runs"][0]["error_message"]
    assert t["allowed_actions"] == ["retry"]
    kinds_dev = [n["kind"] for n in notifications(client, DEV)]
    assert "task_failed" in kinds_dev and "task_failed" in [n["kind"] for n in notifications(client, PM)]
    api.post(f"/api/tasks/{tid}/retry")
    t = api.get(tid)
    assert t["status"] == "In Review" and len(t["runs"]) == 2 and t["runs"][1]["status"] == "completed"
    assert {"agent.error", "task.retry"} <= set(history_actions(t))


def test_repeated_failures_hit_the_retry_limit_and_raise_a_high_risk(api, client, setup):
    project, req = setup
    pid = project["project_id"]
    api.pipeline(pid, retry_limit=1)
    tid = api.task(pid, req["req_id"], "Build login API [fail-llm-always]")["task_id"]
    api.post(f"/api/tasks/{tid}/assign")  # run 1 fails
    api.post(f"/api/tasks/{tid}/retry")  # run 2 fails
    r = client.post(f"/api/tasks/{tid}/retry", headers=DEV)  # limit (1 retry) exhausted
    assert r.status_code == 409 and r.json()["error"]["code"] == "retry_limit_exceeded"
    t = api.get(tid)
    assert t["status"] == "Failed" and len(t["runs"]) == 2 and t["allowed_actions"] == []
    assert any(n["kind"] == "risk_threshold" for n in notifications(client, PM))


def test_generated_code_over_the_loc_limit_fails_the_run(settings):
    from fastapi.testclient import TestClient

    from app.adapters.llm import GeneratedCode
    from app.main import create_app
    from tests.conftest import Api

    class WordyLLM:
        name = "wordy"

        def generate(self, request):
            body = "\n".join(f"x{i} = {i}" for i in range(300))
            return GeneratedCode(files={"generated/big.py": body}, summary="big")

    client = TestClient(create_app(settings, llm=WordyLLM()))
    api = Api(client)
    project = api.project()
    req = api.requirement(project["project_id"])
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    api.post(f"/api/tasks/{tid}/assign")
    t = api.get(tid)
    assert t["status"] == "Failed" and "above the pipeline limit of 200" in t["runs"][0]["error_message"]


# -- deployment (FR-9) --------------------------------------------------------------------------------------------
def test_failed_deployment_rolls_back_and_task_stays_ready(api, client, setup, app):  # UC-07 alt 3a
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"], "Build login API [fail-deploy]")["task_id"]
    advance_to(api, tid, "Ready for Deployment")
    out = api.post(f"/api/tasks/{tid}/deploy")
    assert out["outcome"] == "failed" and out["task"]["status"] == "Ready for Deployment"
    assert app.state.runtime.git.read_main(project["project_id"]) == {}  # merge rolled back
    t = api.get(tid)
    assert t["deployments"][0]["status"] == "failed" and "task.deploy_authorise" in history_actions(t)
    assert "deployment_failed" in [n["kind"] for n in notifications(client, PM)]
    out = api.post(f"/api/tasks/{tid}/deploy")  # second attempt succeeds
    assert out["outcome"] == "succeeded" and api.get(tid)["status"] == "Deployed"


def test_pm_may_authorise_deployment_and_environment_is_validated(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "Ready for Deployment")
    assert client.post(f"/api/tasks/{tid}/deploy", json={"environment": "moon"}, headers=PM).status_code == 422
    out = api.post(f"/api/tasks/{tid}/deploy", headers=PM, json={"environment": "production"})
    assert out["outcome"] == "succeeded" and out["deployment"]["environment"] == "production"
    assert next(h for h in api.get(tid)["history"] if h["action"] == "task.deploy_authorise")["user_id"] == 1


def test_deploy_is_refused_when_deployment_agent_inactive(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "Ready for Deployment")
    api.pipeline(project["project_id"], active_agents=["code_generation", "testing"])
    r = client.post(f"/api/tasks/{tid}/deploy", headers=DEV)
    assert r.status_code == 409 and r.json()["error"]["code"] == "agent_inactive"
    assert api.get(tid)["status"] == "Ready for Deployment"


def test_deployed_is_final(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    advance_to(api, tid, "Deployed")
    for action in ("assign", "approve", "retry", "tests", "deploy"):
        assert client.post(f"/api/tasks/{tid}/{action}", json={"comments": "x"}, headers=DEV).status_code == 409
    assert api.get(tid)["allowed_actions"] == []


def test_diff_before_generation_is_a_precondition_error(api, client, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    r = client.get(f"/api/tasks/{tid}/diff", headers=DEV)
    assert r.status_code == 409 and r.json()["error"]["code"] == "precondition_failed"


def test_timestamps_are_utc_iso_with_a_single_z(api, setup):
    project, req = setup
    tid = api.task(project["project_id"], req["req_id"])["task_id"]
    t = api.get(tid)
    for value in (t["created_at"], t["status_changed_at"], t["history"][0]["timestamp"]):
        assert value.endswith("Z") and "+" not in value and value.count("Z") == 1
        __import__("datetime").datetime.fromisoformat(value.replace("Z", "+00:00"))
