"""PLAN-13 / NFR-5: what happens to agent jobs that a stopped application left behind."""
from __future__ import annotations

import pytest

from app.services import orchestrator
from tests.jobs_support import Crash, CrashingLLM, boot, fire_as_developer, new_task, snapshot  # noqa: F401


def recover_now(app) -> list:
    """Run recovery synchronously and deterministically (no background thread)."""
    rt = app.state.runtime
    jobs = orchestrator.recover_interrupted(rt)
    orchestrator.run_recovered_jobs(rt, jobs)
    return jobs


def crash_during_generation(boot, **task_kwargs) -> tuple[int, dict]:
    """Leave a task in Generating with a `running` run, as a killed process would. Returns (task_id, settings app)."""
    app = boot(llm=CrashingLLM())
    tid = new_task(app, **task_kwargs)
    rt = app.state.runtime
    fire_as_developer(rt, tid, "assign")
    with pytest.raises(Crash):
        orchestrator.run_generation(rt, tid)
    state = snapshot(rt, tid)
    assert state["status"] == "Generating" and state["runs"] == [("running", None)]
    return tid, state


def test_start_on_an_empty_database_recovers_nothing(boot):
    app = boot(recover=True)
    assert app.state.runtime.recovery_thread is None
    assert orchestrator.recover_interrupted(app.state.runtime) == []


def test_interrupted_generation_is_closed_as_failed_and_run_again(boot):
    tid, _ = crash_during_generation(boot)
    app = boot(recover=True)  # the next application start
    app.state.runtime.recovery_thread.join(20)
    state = snapshot(app.state.runtime, tid)
    assert state["status"] == "In Review"
    assert state["runs"] == [("failed", orchestrator.INTERRUPTED), ("completed", None)]  # never "successful"
    assert state["audit"].count("agent.error") == 1 and state["audit"][-1] == "agent.generate"


def test_assigned_task_whose_job_never_started_is_generated(boot):
    app = boot()
    tid = new_task(app)
    fire_as_developer(app.state.runtime, tid, "assign")  # committed, then the process died before the job ran
    assert snapshot(app.state.runtime, tid)["runs"] == []
    recover_now(boot())
    state = snapshot(boot().state.runtime, tid)
    assert state["status"] == "In Review" and state["runs"] == [("completed", None)]


def test_testing_task_whose_job_never_ran_is_tested(boot):
    app = boot()
    tid = new_task(app)
    rt = app.state.runtime
    fire_as_developer(rt, tid, "assign")
    orchestrator.run_generation(rt, tid)
    fire_as_developer(rt, tid, "approve", "looks good")  # committed, then the process died before run_tests
    assert snapshot(rt, tid)["status"] == "Testing" and snapshot(rt, tid)["tests"] == 0
    recover_now(boot())
    state = snapshot(rt, tid)
    assert state["status"] == "Ready for Deployment" and state["tests"] == 1


def test_rework_feedback_is_restored_from_the_audit_trail(boot):
    app = boot()
    tid = new_task(app)
    rt = app.state.runtime
    fire_as_developer(rt, tid, "assign")
    orchestrator.run_generation(rt, tid)
    fire_as_developer(rt, tid, "reject", "please use snake_case names")  # process died before the rework job
    jobs = orchestrator.recover_interrupted(rt)
    assert [(j.kind, j.task_id, j.feedback) for j in jobs] == [("generation", tid, "please use snake_case names")]
    orchestrator.run_recovered_jobs(rt, jobs)
    assert snapshot(rt, tid)["status"] == "In Review"
    assert "please use snake_case names" in str(rt.git.diff(1, snapshot_branch(rt, tid)))


def snapshot_branch(rt, tid) -> str:
    from app.models import AgentRun
    from sqlalchemy import select

    with rt.session_factory() as db:
        return db.scalars(select(AgentRun).where(AgentRun.task_id == tid).order_by(AgentRun.run_id.desc())).first().branch_name


def test_repeated_startup_changes_nothing_more(boot):
    tid, _ = crash_during_generation(boot)
    first = boot(recover=True)
    first.state.runtime.recovery_thread.join(20)
    settled = snapshot(first.state.runtime, tid)
    for _ in range(3):  # restart again and again
        again = boot(recover=True)
        assert again.state.runtime.recovery_thread is None  # nothing left to re-dispatch
    assert snapshot(first.state.runtime, tid) == settled


def test_recovery_called_twice_before_dispatch_writes_nothing_the_second_time(boot):
    tid, _ = crash_during_generation(boot)
    rt = boot().state.runtime
    first = orchestrator.recover_interrupted(rt)
    after_first = snapshot(rt, tid)
    second = orchestrator.recover_interrupted(rt)
    assert first == second and snapshot(rt, tid) == after_first
    assert after_first["audit"].count("agent.error") == 1  # the interruption is recorded once


def test_no_retries_left_fails_the_task_instead_of_starting_another_run(boot):
    tid, _ = crash_during_generation(boot, retry_limit=0)  # the interrupted run was the only run allowed
    app = boot(recover=True)
    assert app.state.runtime.recovery_thread is None  # nothing re-dispatched
    state = snapshot(app.state.runtime, tid)
    assert state["status"] == "Failed" and state["runs"] == [("failed", orchestrator.INTERRUPTED)]
    assert state["audit"][-1] == "agent.error" and state["notifications"] >= 2  # developer and PM were told


def test_the_retry_limit_bounds_repeated_interruptions(boot):
    tid, _ = crash_during_generation(boot, retry_limit=1)
    again = boot(llm=CrashingLLM())  # the re-run is interrupted too
    with pytest.raises(Crash):
        recover_now(again)
    assert snapshot(again.state.runtime, tid)["runs"] == [("failed", orchestrator.INTERRUPTED), ("running", None)]
    final = boot()
    recover_now(final)
    state = snapshot(final.state.runtime, tid)
    assert state["status"] == "Failed" and [r[0] for r in state["runs"]] == ["failed", "failed"]  # 1 run + 1 retry, no more


def test_testing_task_waiting_for_a_person_is_left_alone(boot):
    app = boot()
    tid = new_task(app, title="Strict [fail-tests-always]", retry_limit=0)
    rt = app.state.runtime
    fire_as_developer(rt, tid, "assign")
    orchestrator.run_generation(rt, tid)
    fire_as_developer(rt, tid, "approve")
    orchestrator.run_tests(rt, tid)  # fails; no rework left, so it stays in Testing with a result
    before = snapshot(rt, tid)
    assert before["status"] == "Testing" and before["tests"] == 1
    for _ in range(2):
        recover_now(boot(recover=True))
    assert snapshot(rt, tid) == before  # no extra result, audit row or notification


def test_testing_task_whose_agent_crashed_is_not_silently_rerun(boot, monkeypatch):
    app = boot()
    tid = new_task(app)
    rt = app.state.runtime
    fire_as_developer(rt, tid, "assign")
    orchestrator.run_generation(rt, tid)
    fire_as_developer(rt, tid, "approve")
    monkeypatch.setattr(rt.testing, "run", lambda **_: (_ for _ in ()).throw(RuntimeError("runner exploded")))
    orchestrator.run_tests(rt, tid)  # reported to the developer; the task stays in Testing without a result
    before = snapshot(rt, tid)
    assert before["status"] == "Testing" and before["tests"] == 0 and before["audit"][-1] == "agent.error"
    recover_now(boot(recover=True))
    assert snapshot(rt, tid) == before


def test_tasks_that_are_not_mid_job_are_never_touched(boot):
    app = boot()
    rt = app.state.runtime
    created = new_task(app)
    in_review = new_task(app, "Second task")
    fire_as_developer(rt, in_review, "assign")
    orchestrator.run_generation(rt, in_review)
    failed = new_task(app, "Third [fail-llm-always]")
    fire_as_developer(rt, failed, "assign")
    orchestrator.run_generation(rt, failed)  # fails normally -> Failed
    before = {t: snapshot(rt, t) for t in (created, in_review, failed)}
    assert [before[t]["status"] for t in (created, in_review, failed)] == ["Created", "In Review", "Failed"]
    assert orchestrator.recover_interrupted(boot().state.runtime) == []
    assert {t: snapshot(rt, t) for t in before} == before


def test_recovery_can_be_switched_off(boot):
    tid, _ = crash_during_generation(boot)
    app = boot(recover=False)
    assert app.state.runtime.recovery_thread is None
    assert snapshot(app.state.runtime, tid)["status"] == "Generating"  # untouched until recovery is run
