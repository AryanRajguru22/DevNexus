"""PLAN-07: orchestrator edge cases and crash paths not reached by the API, guard or recovery tests.

Each test drives the real orchestrator against a temporary SQLite file. Agent failures are injected with
monkeypatch or a small fake adapter; nothing in app/ is changed. Where a safety net can only be reached through
inconsistent data, `force_status` writes the status directly and says so.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app import workflow
from app.main import create_app
from app.models import AuditLog, Notification, Task
from app.services import orchestrator
from app.services.tasks import fire
from tests.conftest import DEV, DEV1_ID, PM_ID, Api, advance_to
from tests.jobs_support import boot, fire_as_developer, new_task, snapshot  # noqa: F401


def force_status(rt, task_id: int, status: str) -> None:
    """Bypasses the workflow on purpose: builds the inconsistent state that only a safety net handles."""
    with rt.session_factory() as db:
        db.execute(update(Task).where(Task.task_id == task_id).values(status=status))
        db.commit()


def notifications_for(rt, task_id: int) -> list[tuple[int, str, str]]:
    with rt.session_factory() as db:
        rows = db.scalars(select(Notification).where(Notification.task_id == task_id).order_by(Notification.notification_id))
        return [(n.user_id, n.kind, n.message) for n in rows]


def ready_for_deployment(app) -> int:
    tid = new_task(app)
    advance_to(Api(TestClient(app)), tid, "Ready for Deployment")
    return tid


class ExplodingLLM:
    """Fails with an exception type the code-generation agent does not translate into AgentError."""

    name = "exploding-test-llm"

    def generate(self, request):
        raise RuntimeError("provider returned malformed JSON")


class ExplodingCICD:
    """A CI/CD runner that raises (network error) instead of returning a failed result."""

    def deploy(self, *, branch, environment, attempt, hints):
        raise ConnectionError("CI runner unreachable")


# -- code generation ------------------------------------------------------------------------------------------------
def test_unexpected_llm_exception_fails_the_task_and_leaves_no_running_run(boot, caplog):
    app = boot(llm=ExplodingLLM())
    rt = app.state.runtime
    tid = new_task(app)
    fire_as_developer(rt, tid, "assign")
    with caplog.at_level(logging.ERROR, logger="devnexus.orchestrator"):
        orchestrator.run_generation(rt, tid)
    state = snapshot(rt, tid)
    assert state["status"] == "Failed"
    assert state["runs"] == [("failed", "provider returned malformed JSON")]  # closed, never left `running`
    assert state["audit"][-2:] == ["agent.start", "agent.error"]
    assert sorted((uid, kind) for uid, kind, _ in notifications_for(rt, tid)) == [
        (PM_ID, "task_failed"), (DEV1_ID, "task_failed"),
    ]
    assert "unexpected error in code generation" in caplog.text  # logged with a traceback, unlike an AgentError
    assert Api(TestClient(app)).get(tid)["allowed_actions"] == ["retry"]


def test_rework_job_that_loses_its_claim_creates_no_run(boot, monkeypatch):
    """Rework job read the task as Generating; before it claims the row another job moves the task on."""
    app = boot()
    rt = app.state.runtime
    tid = new_task(app)
    fire_as_developer(rt, tid, "assign")
    orchestrator.run_generation(rt, tid)
    fire_as_developer(rt, tid, "reject", "use snake_case")  # Generating; the rework job has not run yet
    real_claim = orchestrator.claim

    def claim_after_another_job_moved_it(db, task, expected_status):
        with rt.session_factory() as other:
            agent = workflow.Actor(agent=orchestrator.get_agent(other, "code_generation"))
            fire(other, other.get(Task, tid), "agent_error", agent, detail="another job failed it first")
            other.commit()
        return real_claim(db, task, expected_status)

    monkeypatch.setattr(orchestrator, "claim", claim_after_another_job_moved_it)
    before = snapshot(rt, tid)
    orchestrator.run_generation(rt, tid, feedback="use snake_case")
    state = snapshot(rt, tid)
    assert state["status"] == "Failed"  # the other job's outcome stands
    assert state["runs"] == [("completed", None)]  # the losing job started no second run
    assert state["audit"].count("agent.generate") == 1
    # Only the competing job's row was written; the loser rolled back without audit rows or notifications
    # (fire() records the transition but notifies nobody).
    assert state["audit"] == before["audit"] + ["agent.error"]
    assert state["audit_total"] == before["audit_total"] + 1
    assert state["notifications"] == before["notifications"]


def test_slow_agent_pauses_while_the_task_shows_generating_and_testing(settings, monkeypatch):
    """DEVNEXUS_MOCK_AGENT_DELAY: the pause happens after the state is committed, so the UI can show it."""
    app = create_app(replace(settings, mock_agent_delay=0.25, recover_on_startup=False))
    rt = app.state.runtime
    try:
        tid = new_task(app)  # inside try: the engine is disposed even if setup fails
        during_pause = []
        monkeypatch.setattr(orchestrator, "time", SimpleNamespace(sleep=lambda s: during_pause.append((s, snapshot(rt, tid)))))
        fire_as_developer(rt, tid, "assign")
        orchestrator.run_generation(rt, tid)
        fire_as_developer(rt, tid, "approve")
        orchestrator.run_tests(rt, tid)
        assert [delay for delay, _ in during_pause] == [0.25, 0.25]
        generating, testing = (s for _, s in during_pause)
        assert generating["status"] == "Generating" and generating["runs"] == [("running", None)]
        assert testing["status"] == "Testing" and testing["tests"] == 0
        assert snapshot(rt, tid)["status"] == "Ready for Deployment"
    finally:
        app.state.runtime.engine.dispose()


# -- automated tests ------------------------------------------------------------------------------------------------
def test_testing_agent_crash_notifies_the_developer_and_a_rerun_completes(boot, monkeypatch):
    app = boot()
    rt = app.state.runtime
    client = TestClient(app)
    tid = new_task(app)
    fire_as_developer(rt, tid, "assign")
    orchestrator.run_generation(rt, tid)
    fire_as_developer(rt, tid, "approve")
    monkeypatch.setattr(rt.testing, "run", lambda **_: (_ for _ in ()).throw(RuntimeError("runner exploded")))
    sent_before, total_before = notifications_for(rt, tid), snapshot(rt, tid)["notifications"]
    orchestrator.run_tests(rt, tid)
    state = snapshot(rt, tid)
    assert state["status"] == "Testing" and state["tests"] == 0 and state["audit"][-1] == "agent.error"
    sent = notifications_for(rt, tid)
    assert sent[: len(sent_before)] == sent_before and state["notifications"] == total_before + 1
    [(uid, kind, message)] = sent[len(sent_before):]  # exactly one new notification
    assert (uid, kind) == (DEV1_ID, "tests_failed")  # developer only; the PM is not told about a crashed runner
    assert "could not complete" in message
    assert Api(client).get(tid)["allowed_actions"] == ["tests"]
    monkeypatch.undo()
    assert client.post(f"/api/tasks/{tid}/tests", headers=DEV).status_code == 200  # the documented way out
    state = snapshot(rt, tid)
    assert state["status"] == "Ready for Deployment" and state["tests"] == 1


def test_tests_job_without_a_completed_run_records_an_error_and_changes_nothing(boot):
    app = boot()
    rt = app.state.runtime
    tid = new_task(app)
    force_status(rt, tid, "Testing")  # Testing with no completed code-generation run: not reachable via the API
    before = snapshot(rt, tid)
    orchestrator.run_tests(rt, tid)
    after = snapshot(rt, tid)
    assert after["status"] == "Testing" and after["tests"] == 0 and after["runs"] == []
    assert after["audit"] == before["audit"] + ["agent.error"] and after["notifications"] == before["notifications"]
    with rt.session_factory() as db:
        row = db.scalars(select(AuditLog).order_by(AuditLog.log_id.desc())).first()
        assert row.agent.type == "testing" and row.user_id is None
        assert row.detail == "no completed code-generation run to test"


def test_recovery_does_not_redispatch_tests_for_a_task_with_no_completed_run(boot):
    app = boot()
    rt = app.state.runtime
    tid = new_task(app)
    force_status(rt, tid, "Testing")
    before = snapshot(rt, tid)
    assert orchestrator.recover_interrupted(rt) == []
    assert snapshot(rt, tid) == before


# -- deployment -----------------------------------------------------------------------------------------------------
def test_deployment_agent_crash_is_recorded_as_failed_and_the_task_stays_ready(boot, monkeypatch):
    app = boot()
    rt = app.state.runtime
    client = TestClient(app)
    tid = ready_for_deployment(app)
    pid = Api(client).get(tid)["project_id"]
    monkeypatch.setattr(rt.deployment, "deploy", lambda **_: (_ for _ in ()).throw(RuntimeError("agent exploded")))
    out = client.post(f"/api/tasks/{tid}/deploy", headers=DEV).json()
    assert out["outcome"] == "failed" and out["message"] == "Deployment agent error: agent exploded"
    assert out["task"]["status"] == "Ready for Deployment" and out["deployment"]["status"] == "failed"
    state = snapshot(rt, tid)
    assert state["deployments"] == 1 and state["audit"][-1] == "task.deploy_authorise"  # authorisation kept
    with rt.session_factory() as db:
        agent_row = db.scalars(select(AuditLog).where(AuditLog.action == "agent.deploy")).one()
        assert agent_row.target_ref == f"deployment:{out['deployment']['deploy_id']}" and "agent exploded" in agent_row.detail
    assert sorted((uid, kind) for uid, kind, _ in notifications_for(rt, tid) if kind.startswith("deployment")) == [
        (PM_ID, "deployment_failed"), (DEV1_ID, "deployment_failed"),
    ]
    assert rt.git.read_main(pid) == {}  # the agent failed before merging
    monkeypatch.undo()
    assert client.post(f"/api/tasks/{tid}/deploy", headers=DEV).json()["outcome"] == "succeeded"
    assert snapshot(rt, tid)["status"] == "Deployed"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,  # only the rollback assertion may fail; any other error is a real test failure
    reason="M-2, issue #16 (TEST_PLAN 5.2): DeploymentAgent rolls back only when CI/CD returns a failure, not when it raises",
)
def test_ci_runner_raising_after_the_merge_leaves_main_restored(settings):
    app = create_app(replace(settings, recover_on_startup=False), cicd=ExplodingCICD())
    try:
        client = TestClient(app)
        tid = ready_for_deployment(app)
        pid = Api(client).get(tid)["project_id"]
        out = client.post(f"/api/tasks/{tid}/deploy", headers=DEV).json()
        assert out["outcome"] == "failed" and out["task"]["status"] == "Ready for Deployment"
        assert app.state.runtime.git.read_main(pid) == {}  # UC-07 3a, NFR-6: a failed deployment leaves no trace
    finally:
        app.state.runtime.engine.dispose()


def test_deploy_without_a_completed_run_is_refused_and_writes_nothing(boot):
    app = boot()
    rt = app.state.runtime
    client = TestClient(app)
    tid = new_task(app)
    force_status(rt, tid, "Ready for Deployment")  # no code-generation run exists: not reachable via the API
    before = snapshot(rt, tid)
    r = client.post(f"/api/tasks/{tid}/deploy", headers=DEV)
    assert r.status_code == 409 and r.json()["error"]["code"] == "precondition_failed"
    after = snapshot(rt, tid)
    assert after == before  # no deployment, no authorisation row, no notification: the claim was rolled back
    assert rt.git.read_main(Api(client).get(tid)["project_id"]) == {}


# -- start-up recovery ----------------------------------------------------------------------------------------------
def test_a_recovery_job_that_raises_does_not_stop_the_others(boot, monkeypatch, caplog):
    app = boot()
    rt = app.state.runtime
    broken, healthy = new_task(app, "First task"), new_task(app, "Second task")
    for tid in (broken, healthy):
        fire_as_developer(rt, tid, "assign")  # committed; the process stopped before the jobs ran
    jobs = orchestrator.recover_interrupted(rt)
    assert [(j.kind, j.task_id) for j in jobs] == [("generation", broken), ("generation", healthy)]
    real_run_generation = orchestrator.run_generation

    def run_generation(rt_, task_id, feedback=None):
        if task_id == broken:
            raise RuntimeError("workspace disk full")
        return real_run_generation(rt_, task_id, feedback)

    monkeypatch.setattr(orchestrator, "run_generation", run_generation)
    with caplog.at_level(logging.ERROR, logger="devnexus.orchestrator"):
        orchestrator.run_recovered_jobs(rt, jobs)
    assert snapshot(rt, broken)["status"] == "Assigned"  # untouched, so the next start will try again
    assert snapshot(rt, healthy)["status"] == "In Review"
    assert f"recovery job generation for task {broken} failed" in caplog.text
