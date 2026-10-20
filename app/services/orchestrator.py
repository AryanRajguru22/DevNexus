"""Agent Orchestrator (FR-3, FR-5, FR-6, FR-8, FR-9): runs the agents for a task and records the outcome.

Code generation and testing run as background jobs (one fresh DB session each); deployment runs in the request.
All state changes go through workflow.apply_event via services.tasks.fire.

Duplicate protection (PLAN-14): every transition is claimed with a compare-and-set on the stored status
(services.tasks.claim), and a generation job refuses to start while a run of the task is still `running`. Both are
enforced in the database, so a double-click, a repeated request or a second job cannot create a second run.
Start-up recovery (PLAN-13): recover_interrupted / run_recovered_jobs, see the end of this module.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit, notifications, workflow
from ..agents.base import AgentError
from ..enums import AgentType, DeploymentStatus, NotificationKind, RunStatus, TaskStatus
from ..errors import ApiError
from ..models import Agent, AgentRun, AuditLog, Deployment, Requirement, Task, TestResult, User, utcnow
from ..schemas import DeployOutcome, DeploymentOut
from ..validation import load_pipeline
from . import analytics
from .runtime import Runtime
from .tasks import branch_for, claim, claim_or_conflict, fire, get_agent, hints_for, task_out

log = logging.getLogger("devnexus.orchestrator")


def _latest_completed_run(db: Session, task: Task) -> AgentRun | None:
    return db.scalars(
        select(AgentRun)
        .where(AgentRun.task_id == task.task_id, AgentRun.status == RunStatus.COMPLETED.value)
        .order_by(AgentRun.run_id.desc())
        .limit(1)
    ).first()


def _count_for_task(db: Session, model, task: Task) -> int:
    return db.scalar(
        select(func.count()).select_from(model).join(AgentRun, model.run_id == AgentRun.run_id)
        .where(AgentRun.task_id == task.task_id)
    ) or 0


def _has_running_run(db: Session, task: Task) -> bool:
    return db.scalar(
        select(AgentRun.run_id)
        .where(AgentRun.task_id == task.task_id, AgentRun.status == RunStatus.RUNNING.value)
        .limit(1)
    ) is not None


def _log_refused(err: ApiError, what: str, task_id: int) -> None:
    """A lost race (another request/job already moved the task) is expected and quiet; anything else is logged."""
    if err.code == "invalid_transition":
        log.info("%s for task %s ignored: %s", what, task_id, err.message)
    else:
        log.exception("%s for task %s refused", what, task_id)


def _fail_generation(db: Session, task: Task, actor: workflow.Actor, message: str) -> None:
    """Generating -> Failed (agent_error), tell the developer and PM, re-evaluate project risk. Caller commits."""
    fire(db, task, "agent_error", actor, detail=message)
    notifications.notify(
        db, kind=NotificationKind.TASK_FAILED, project=task.project, task=task, to_developer=True, to_manager=True,
        message=f"Task '{task.title}' failed during code generation: {message}",
    )
    analytics.check_risk_threshold(db, task.project)


def _pause(rt: Runtime) -> None:
    if rt.settings.mock_agent_delay > 0:
        time.sleep(rt.settings.mock_agent_delay)


# -- code generation (FR-5) -----------------------------------------------------------------------------------------
def run_generation(rt: Runtime, task_id: int, feedback: str | None = None) -> None:
    """Continue a task that is Assigned (first run / retry) or Generating (rework) until In Review or Failed."""
    with rt.session_factory() as db:
        task = db.get(Task, task_id)
        if task is None or task.status not in (TaskStatus.ASSIGNED.value, TaskStatus.GENERATING.value):
            return
        agent = get_agent(db, AgentType.CODE_GENERATION.value)
        actor = workflow.Actor(agent=agent)
        try:
            if task.status == TaskStatus.ASSIGNED.value:
                fire(db, task, "agent_start", actor)  # claims the task: only one of two duplicate jobs gets past here
            elif not claim(db, task, TaskStatus.GENERATING.value):  # rework: same guard, there is no transition
                db.rollback()
                log.info("generation for task %s ignored: it is no longer Generating", task_id)
                return
            if _has_running_run(db, task):  # the write lock is held, so this check and the insert below are atomic
                db.rollback()
                log.info("generation for task %s ignored: a run is already in progress", task_id)
                return
            run = AgentRun(task_id=task.task_id, agent_id=agent.agent_id, branch_name=branch_for(task))
            db.add(run)
            db.commit()
        except ApiError as err:
            db.rollback()
            _log_refused(err, "start of generation", task_id)
            return
        attempt = workflow.run_count(db, task)
        project = task.project
        max_loc = load_pipeline(project.pipeline_config).constraints.max_loc
        requirement = db.get(Requirement, task.req_id)
        _pause(rt)
        try:
            result = rt.codegen.run(
                project_id=task.project_id, branch=run.branch_name, title=task.title, description=task.description,
                requirement=requirement.description, feedback=feedback, attempt=attempt, max_loc=max_loc,
            )
        except Exception as exc:  # noqa: BLE001 - any agent failure must end in the Failed state, never hang
            if not isinstance(exc, AgentError):
                log.exception("unexpected error in code generation for task %s", task_id)
            run.status, run.finished_at, run.error_message = RunStatus.FAILED.value, utcnow(), str(exc)
            _fail_generation(db, task, actor, str(exc))
            db.commit()
            return
        run.status, run.finished_at = RunStatus.COMPLETED.value, utcnow()
        fire(db, task, "code_ready", actor, detail=result.summary)
        notifications.notify(
            db, kind=NotificationKind.CODE_READY, project=project, task=task, to_developer=True,
            message=f"Code for '{task.title}' is ready for review on branch {run.branch_name}.",
        )
        db.commit()


# -- automated tests (FR-8) -----------------------------------------------------------------------------------------
def run_tests(rt: Runtime, task_id: int) -> None:
    """Run the Testing Agent for a task in Testing; pass -> Ready for Deployment, fail -> rework (if allowed)."""
    rework_feedback: str | None = None
    with rt.session_factory() as db:
        task = db.get(Task, task_id)
        if task is None or task.status != TaskStatus.TESTING.value:
            return
        agent = get_agent(db, AgentType.TESTING.value)
        actor = workflow.Actor(agent=agent)
        project = task.project
        run = _latest_completed_run(db, task)
        if run is None:
            audit.record(db, agent=agent, action="agent.error", target_ref=f"task:{task.task_id}",
                         detail="no completed code-generation run to test")
            db.commit()
            return
        attempt = _count_for_task(db, TestResult, task) + 1
        _pause(rt)
        try:
            outcome = rt.testing.run(
                project_id=task.project_id, branch=run.branch_name, hints=hints_for(task), attempt=attempt
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("testing agent crashed for task %s", task_id)
            audit.record(db, agent=agent, action="agent.error", target_ref=f"task:{task.task_id}", detail=str(exc))
            notifications.notify(
                db, kind=NotificationKind.TESTS_FAILED, project=project, task=task, to_developer=True,
                message=f"The test run for '{task.title}' could not complete: {exc}. Re-run the tests.",
            )
            db.commit()
            return
        db.add(TestResult(
            run_id=run.run_id, passed_count=outcome.passed, failed_count=outcome.failed,
            coverage_pct=outcome.coverage_pct, simulated=True,
        ))
        db.flush()
        try:
            if outcome.failed == 0:
                fire(db, task, "tests_passed", actor, detail=outcome.report)
                notifications.notify(
                    db, kind=NotificationKind.TESTS_PASSED, project=project, task=task, to_developer=True,
                    message=f"All tests passed for '{task.title}' ({outcome.passed} checks). Ready for deployment.",
                )
            else:
                try:
                    fire(db, task, "tests_failed", actor, detail=outcome.report)
                    rework_feedback = outcome.report
                    msg = f"Tests failed for '{task.title}' ({outcome.failed} failed); sent back for rework."
                except ApiError as err:
                    if err.code == "invalid_transition":
                        raise  # another job already decided this task: discard this duplicate outcome (below)
                    # Retry limit reached (already flagged as a risk) or generation agent inactive: stay in Testing.
                    audit.record(db, agent=agent, action="agent.test", target_ref=f"task:{task.task_id}",
                                 detail=f"{outcome.report}\nTask stays in Testing: {err.message}")
                    msg = f"Tests failed for '{task.title}' and the task cannot be reworked: {err.message}"
                notifications.notify(
                    db, kind=NotificationKind.TESTS_FAILED, project=project, task=task, to_developer=True, message=msg
                )
            db.commit()
        except ApiError as err:
            db.rollback()
            _log_refused(err, "test outcome", task_id)
            return
    if rework_feedback is not None:
        run_generation(rt, task_id, feedback=rework_feedback)


# -- deployment (FR-9) ----------------------------------------------------------------------------------------------
def deploy_task(rt: Runtime, db: Session, task: Task, user: User, environment: str | None) -> DeployOutcome:
    """Authorised deployment (UC-07). Synchronous: the outcome is part of the response."""
    actor = workflow.Actor(user=user)
    pipeline = load_pipeline(task.project.pipeline_config)
    workflow.check_event(db, task, "authorise_deployment", actor, pipeline)  # raises on any violation
    # Claim before the agent acts: a second concurrent request waits for this transaction, then finds the task
    # Deployed (409) instead of deploying twice. (Holds the database write lock for the length of the deployment.)
    claim_or_conflict(db, task, "authorise_deployment")
    env = environment or pipeline.constraints.target_environment.value
    run = _latest_completed_run(db, task)
    if run is None:  # unreachable through the workflow, kept as a safety net
        raise ApiError(409, "precondition_failed", "No completed code-generation run to deploy")
    attempt = _count_for_task(db, Deployment, task) + 1
    project = task.project
    # The human authorisation is recorded before the agent acts, so it exists even if the deployment fails.
    audit.record(db, user=user, action="task.deploy_authorise", target_ref=f"task:{task.task_id}",
                 detail=f"authorised deployment to {env}")
    agent = get_agent(db, AgentType.DEPLOYMENT.value)
    _pause(rt)
    try:
        result = rt.deployment.deploy(
            project_id=task.project_id, branch=run.branch_name, environment=env, hints=hints_for(task), attempt=attempt
        )
        ok, message = result.succeeded, result.message
    except Exception as exc:  # noqa: BLE001
        log.exception("deployment agent crashed for task %s", task.task_id)
        ok, message = False, f"Deployment agent error: {exc}"
    deployment = Deployment(
        run_id=run.run_id, environment=env,
        status=(DeploymentStatus.SUCCEEDED if ok else DeploymentStatus.FAILED).value,
    )
    db.add(deployment)
    db.flush()
    audit.record(db, agent=agent, action="agent.deploy", target_ref=f"deployment:{deployment.deploy_id}",
                 detail=f"task:{task.task_id} -> {env}: {message}")
    if ok:
        workflow.apply_event(db, task, "authorise_deployment", actor, audit_entry=False)
        notifications.notify(
            db, kind=NotificationKind.DEPLOYMENT_COMPLETED, project=project, task=task, to_developer=True,
            to_manager=True, message=f"'{task.title}' was deployed to {env}.",
        )
    else:
        notifications.notify(
            db, kind=NotificationKind.DEPLOYMENT_FAILED, project=project, task=task, to_developer=True,
            to_manager=True, message=f"Deployment of '{task.title}' to {env} failed; the task stays Ready for Deployment.",
        )
    db.commit()
    return DeployOutcome(
        outcome="succeeded" if ok else "failed", message=message,
        deployment=DeploymentOut.model_validate(deployment), task=task_out(db, task),
    )


# -- start-up recovery (NFR-5, PLAN-13) -----------------------------------------------------------------------------
INTERRUPTED = "Interrupted: the application stopped before this run finished"


@dataclass(frozen=True)
class RecoveryJob:
    kind: str  # "generation" | "tests"
    task_id: int
    feedback: str | None = None  # rework feedback to hand back to the code-generation agent


def _last_audit(db: Session, task: Task, actions: tuple[str, ...] | None = None) -> AuditLog | None:
    stmt = select(AuditLog).where(AuditLog.target_ref == f"task:{task.task_id}").order_by(AuditLog.log_id.desc()).limit(1)
    if actions is not None:
        stmt = stmt.where(AuditLog.action.in_(actions))
    return db.scalars(stmt).first()


def _rework_feedback(db: Session, task: Task) -> str | None:
    """The feedback that put the task into Generating, read back from the audit trail (the in-memory copy is lost)."""
    entry = _last_audit(db, task, ("agent.start", "task.reject", "agent.test"))
    return entry.detail if entry is not None and entry.action in ("task.reject", "agent.test") else None


def recover_interrupted(rt: Runtime) -> list[RecoveryJob]:
    """Repair what a stopped application left behind and return the agent jobs that must run again.

    A job is atomic (its transition, audit row and result commit together), so after a crash a task is either
    untouched (its background job never started: Assigned, Generating, Testing) or has a `running` run whose
    generation never finished. Nothing is ever marked successful:
      * every `running` run is closed as `failed` (error_message `INTERRUPTED`) with an `agent.error` audit row;
      * Assigned -> generation job; Generating -> generation job (rework feedback restored from the audit trail)
        while the retry limit allows another run, otherwise Generating -> Failed through the normal `agent_error`
        transition, which a person can see and (retry limit permitting) retry;
      * Testing -> tests job only when the newest completed run has no test result yet. A Testing task that already
        has a result is waiting for a person (retry limit reached) and a task whose testing agent crashed has been
        reported; both are left alone so a restart never adds results or notifications.
    Idempotent: a second call finds nothing to close and returns the same jobs without writing. Assumes one
    application process per database (nothing else is running a job at start-up).
    """
    jobs: list[RecoveryJob] = []
    with rt.session_factory() as db:
        for run in db.scalars(select(AgentRun).where(AgentRun.status == RunStatus.RUNNING.value).order_by(AgentRun.run_id)):
            run.status, run.finished_at, run.error_message = RunStatus.FAILED.value, utcnow(), INTERRUPTED
            audit.record(
                db, agent=db.get(Agent, run.agent_id), action="agent.error", target_ref=f"task:{run.task_id}",
                detail=f"run {run.run_id} on {run.branch_name} was interrupted by an application restart",
            )
            log.warning("closed interrupted run %s of task %s", run.run_id, run.task_id)
        db.flush()
        open_states = (TaskStatus.ASSIGNED.value, TaskStatus.GENERATING.value, TaskStatus.TESTING.value)
        for task in db.scalars(select(Task).where(Task.status.in_(open_states)).order_by(Task.task_id)):
            if task.status == TaskStatus.ASSIGNED.value:
                jobs.append(RecoveryJob("generation", task.task_id))
            elif task.status == TaskStatus.GENERATING.value:
                pipeline = load_pipeline(task.project.pipeline_config)
                if workflow.rework_allowed(db, task, pipeline):
                    jobs.append(RecoveryJob("generation", task.task_id, _rework_feedback(db, task)))
                else:
                    message = f"{INTERRUPTED}; the retry limit ({pipeline.retry_limit}) leaves no run to re-start"
                    _fail_generation(db, task, workflow.Actor(agent=get_agent(db, AgentType.CODE_GENERATION.value)), message)
                    log.warning("task %s failed: %s", task.task_id, message)
            elif _tests_interrupted(db, task):
                jobs.append(RecoveryJob("tests", task.task_id))
        db.commit()
    return jobs


def _tests_interrupted(db: Session, task: Task) -> bool:
    run = _latest_completed_run(db, task)
    if run is None:
        return False  # nothing to test; run_tests would only write another error row
    if db.scalar(select(func.count()).select_from(TestResult).where(TestResult.run_id == run.run_id)):
        return False  # tests already ran: the task is waiting for a person, not for a job
    last = _last_audit(db, task)
    return not (last is not None and last.action == "agent.error")  # a crashed testing agent was already reported


def run_recovered_jobs(rt: Runtime, jobs: list[RecoveryJob]) -> None:
    """Run the jobs returned by recover_interrupted, one after another; one failing job never stops the rest."""
    for job in jobs:
        try:
            if job.kind == "generation":
                run_generation(rt, job.task_id, job.feedback)
            else:
                run_tests(rt, job.task_id)
        except Exception:  # noqa: BLE001 - recovery must not take the application down
            log.exception("recovery job %s for task %s failed", job.kind, job.task_id)
