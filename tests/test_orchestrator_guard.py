"""PLAN-14: duplicate requests and jobs for the same task produce one run / one result / one deployment.

The guarantee is enforced in the database (compare-and-set on the stored task status plus a running-run check under
the write lock), so these tests use real threads on a real SQLite file, and a deterministic stale-session test for
the exact lost-update the guard exists to prevent.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app import workflow
from app.adapters.llm import MockLLMProvider, UnknownProviderError, create_provider
from app.config import Settings, get_settings
from app.errors import ApiError
from app.main import create_app
from app.models import Task, User
from app.services import orchestrator
from app.services.tasks import fire
from tests.conftest import DEV, DEV1_ID, PM, PM_ID
from tests.jobs_support import BlockingLLM, boot, fire_as_developer, new_task, snapshot  # noqa: F401


def ready_for_review(app, title: str = "Build login API") -> int:
    tid = new_task(app, title)
    fire_as_developer(app.state.runtime, tid, "assign")
    orchestrator.run_generation(app.state.runtime, tid)
    return tid


def test_second_generation_job_while_the_first_is_running_creates_no_second_run(boot):
    llm = BlockingLLM()
    app = boot(llm=llm)
    rt = app.state.runtime
    tid = new_task(app)
    fire_as_developer(rt, tid, "assign")
    first = threading.Thread(target=orchestrator.run_generation, args=(rt, tid))
    first.start()
    assert llm.entered.wait(10)  # job 1 is inside the LLM call: task Generating, run `running`
    orchestrator.run_generation(rt, tid)  # duplicate dispatch of the same job
    llm.release.set()
    first.join(20)
    state = snapshot(rt, tid)
    assert llm.calls == 1 and state["runs"] == [("completed", None)] and state["status"] == "In Review"
    assert state["audit"].count("agent.start") == 1 and state["audit"].count("agent.generate") == 1


def test_many_simultaneous_generation_jobs_make_exactly_one_run(boot):
    app = boot()
    rt = app.state.runtime
    tid = new_task(app)
    fire_as_developer(rt, tid, "assign")
    barrier = threading.Barrier(6)

    def job():
        barrier.wait(10)
        orchestrator.run_generation(rt, tid)

    with ThreadPoolExecutor(6) as pool:
        for future in [pool.submit(job) for _ in range(6)]:
            future.result(30)  # no job may blow up (e.g. "database is locked")
    state = snapshot(rt, tid)
    assert state["runs"] == [("completed", None)] and state["status"] == "In Review"
    assert state["audit"].count("agent.start") == 1


def test_a_stale_view_of_the_task_cannot_apply_a_transition_twice(boot):
    """The lost update itself: session A read the task as Assigned, B then moved it on; A must lose, not overwrite."""
    app = boot()
    rt = app.state.runtime
    tid = new_task(app)
    fire_as_developer(rt, tid, "assign")
    with rt.session_factory() as a, rt.session_factory() as b:
        stale = a.get(Task, tid)
        agent = workflow.Actor(agent=orchestrator.get_agent(b, "code_generation"))
        fire(b, b.get(Task, tid), "agent_start", agent)
        b.commit()
        with pytest.raises(ApiError) as err:
            fire(a, stale, "agent_start", agent)
        assert err.value.code == "invalid_transition" and "changed by another request" in err.value.message
        a.rollback()
    assert snapshot(rt, tid)["audit"].count("agent.start") == 1
    assert snapshot(rt, tid)["status"] == "Generating"


def test_concurrent_approvals_start_one_test_run(boot):
    app = boot()
    rt = app.state.runtime
    client = TestClient(app)
    tid = ready_for_review(app)
    barrier = threading.Barrier(4)

    def approve():
        barrier.wait(10)
        return client.post(f"/api/tasks/{tid}/approve", headers=DEV).status_code

    with ThreadPoolExecutor(4) as pool:
        codes = sorted(f.result(60) for f in [pool.submit(approve) for _ in range(4)])
    assert codes == [200, 409, 409, 409]
    state = snapshot(rt, tid)
    assert state["status"] == "Ready for Deployment" and state["tests"] == 1
    assert state["audit"].count("task.approve") == 1 and state["audit"].count("agent.test") == 1


def test_simultaneous_test_jobs_record_one_result(boot):
    app = boot()
    rt = app.state.runtime
    tid = ready_for_review(app)
    fire_as_developer(rt, tid, "approve")
    barrier = threading.Barrier(5)

    def job():
        barrier.wait(10)
        orchestrator.run_tests(rt, tid)

    with ThreadPoolExecutor(5) as pool:
        for future in [pool.submit(job) for _ in range(5)]:
            future.result(60)
    state = snapshot(rt, tid)
    assert state["status"] == "Ready for Deployment" and state["tests"] == 1
    assert state["audit"].count("agent.test") == 1


def test_overlapping_test_jobs_the_late_one_is_discarded(boot, monkeypatch):
    """Deterministic overlap: job 1 is held inside the testing agent while job 2 completes the task."""
    app = boot()
    rt = app.state.runtime
    tid = ready_for_review(app)
    fire_as_developer(rt, tid, "approve")
    entered, release, real_run = threading.Event(), threading.Event(), rt.testing.run
    calls = []

    def slow_first_call(**kwargs):
        calls.append(1)
        if len(calls) == 1:
            entered.set()
            assert release.wait(20)
        return real_run(**kwargs)

    monkeypatch.setattr(rt.testing, "run", slow_first_call)
    first = threading.Thread(target=orchestrator.run_tests, args=(rt, tid))
    first.start()
    assert entered.wait(10)
    orchestrator.run_tests(rt, tid)  # job 2 runs to completion: Testing -> Ready for Deployment
    assert snapshot(rt, tid)["status"] == "Ready for Deployment"
    release.set()
    first.join(20)  # job 1 now finishes with a stale view of the task and must not apply its outcome
    state = snapshot(rt, tid)
    assert len(calls) == 2 and state["tests"] == 1 and state["audit"].count("agent.test") == 1
    assert state["status"] == "Ready for Deployment"


def test_a_losing_duplicate_test_job_does_not_report_a_retry_limit_failure(boot):
    """A duplicate whose tests fail must be discarded, not recorded as 'cannot be reworked'."""
    app = boot()
    rt = app.state.runtime
    tid = ready_for_review(app, "Flaky [fail-tests-always]")
    fire_as_developer(rt, tid, "approve")
    barrier = threading.Barrier(3)

    def job():
        barrier.wait(10)
        orchestrator.run_tests(rt, tid)

    with ThreadPoolExecutor(3) as pool:
        for future in [pool.submit(job) for _ in range(3)]:
            future.result(60)
    state = snapshot(rt, tid)
    assert state["tests"] == 1 and state["audit"].count("agent.test") == 1
    assert not any("cannot be reworked" in a for a in state["audit"])


def test_concurrent_deploy_requests_deploy_once(boot):
    app = boot()
    rt = app.state.runtime
    client = TestClient(app)
    tid = ready_for_review(app)
    fire_as_developer(rt, tid, "approve")
    orchestrator.run_tests(rt, tid)
    assert snapshot(rt, tid)["status"] == "Ready for Deployment"
    barrier = threading.Barrier(3)

    def deploy():
        barrier.wait(10)
        return client.post(f"/api/tasks/{tid}/deploy", headers=PM).status_code

    with ThreadPoolExecutor(3) as pool:
        codes = sorted(f.result(60) for f in [pool.submit(deploy) for _ in range(3)])
    assert codes == [200, 409, 409]
    state = snapshot(rt, tid)
    assert state["status"] == "Deployed" and state["deployments"] == 1


def test_a_stale_deploy_request_is_refused_without_a_second_deployment(boot):
    app = boot()
    rt = app.state.runtime
    tid = ready_for_review(app)
    fire_as_developer(rt, tid, "approve")
    orchestrator.run_tests(rt, tid)
    with rt.session_factory() as stale_db, rt.session_factory() as db:
        stale_task = stale_db.get(Task, tid)
        orchestrator.deploy_task(rt, db, db.get(Task, tid), db.get(User, PM_ID), None)
        with pytest.raises(ApiError) as err:
            orchestrator.deploy_task(rt, stale_db, stale_task, stale_db.get(User, PM_ID), None)
        assert err.value.status_code == 409
        stale_db.rollback()
    assert snapshot(rt, tid)["deployments"] == 1


def test_a_job_for_a_task_that_already_moved_on_does_nothing(boot):
    app = boot()
    rt = app.state.runtime
    tid = ready_for_review(app)
    before = snapshot(rt, tid)
    orchestrator.run_generation(rt, tid)  # task is In Review: not Assigned/Generating
    orchestrator.run_tests(rt, tid)  # ... and not Testing
    assert snapshot(rt, tid) == before


def test_rework_after_rejection_still_works_with_the_guard(boot):
    app = boot()
    client = TestClient(app)
    tid = ready_for_review(app)
    assert client.post(f"/api/tasks/{tid}/reject", headers=DEV, json={"comments": "rename the handler"}).status_code == 200
    state = snapshot(app.state.runtime, tid)
    assert state["status"] == "In Review" and [r[0] for r in state["runs"]] == ["completed", "completed"]


# -- selectable LLM provider (PLAN-14, second half) -----------------------------------------------------------------
def test_default_provider_is_the_labelled_mock():
    assert isinstance(create_provider("mock"), MockLLMProvider)
    assert "not a real model" in create_provider("mock").name


def test_unknown_provider_fails_fast_with_a_clear_message(tmp_path):
    settings = Settings(data_dir=tmp_path, database_url=f"sqlite:///{(tmp_path / 'x.db').as_posix()}", llm_provider="gpt-9")
    with pytest.raises(UnknownProviderError, match=r"Unknown LLM provider 'gpt-9'.*DEVNEXUS_LLM_PROVIDER.*mock"):
        create_app(settings)
    assert not (tmp_path / "x.db").exists()  # failed before touching the database


def test_provider_and_recovery_come_from_the_environment(monkeypatch):
    monkeypatch.delenv("DEVNEXUS_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEVNEXUS_RECOVER_ON_STARTUP", raising=False)
    defaults = get_settings()
    assert defaults.llm_provider == "mock" and defaults.recover_on_startup is True
    monkeypatch.setenv("DEVNEXUS_LLM_PROVIDER", " Mock ")
    monkeypatch.setenv("DEVNEXUS_RECOVER_ON_STARTUP", "0")
    configured = get_settings()
    assert configured.llm_provider == "mock" and configured.recover_on_startup is False
