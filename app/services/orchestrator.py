"""Agent Orchestrator (FR-3, FR-5, FR-6, FR-8, FR-9): runs the agents for a task and records the outcome.

Code generation and testing run as background jobs (one fresh DB session each); deployment runs in the request.
All state changes go through workflow.apply_event via services.tasks.fire.
"""
from __future__ import annotations

import logging
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit, notifications, workflow
from ..agents.base import AgentError
from ..enums import AgentType, DeploymentStatus, NotificationKind, RunStatus, TaskStatus
from ..errors import ApiError
from ..models import AgentRun, Deployment, Requirement, Task, TestResult, User, utcnow
from ..schemas import DeployOutcome, DeploymentOut
from ..validation import load_pipeline
from . import analytics
from .runtime import Runtime
from .tasks import branch_for, fire, get_agent, hints_for, task_out

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
                fire(db, task, "agent_start", actor)
            run = AgentRun(task_id=task.task_id, agent_id=agent.agent_id, branch_name=branch_for(task))
            db.add(run)
            db.commit()
        except ApiError:
            db.rollback()
            log.exception("could not start generation for task %s", task_id)
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
            fire(db, task, "agent_error", actor, detail=str(exc))
            notifications.notify(
                db, kind=NotificationKind.TASK_FAILED, project=project, task=task, to_developer=True, to_manager=True,
                message=f"Task '{task.title}' failed during code generation: {exc}",
            )
            analytics.check_risk_threshold(db, project)
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
                    # Retry limit reached (already flagged as a risk) or generation agent inactive: stay in Testing.
                    audit.record(db, agent=agent, action="agent.test", target_ref=f"task:{task.task_id}",
                                 detail=f"{outcome.report}\nTask stays in Testing: {err.message}")
                    msg = f"Tests failed for '{task.title}' and the task cannot be reworked: {err.message}"
                notifications.notify(
                    db, kind=NotificationKind.TESTS_FAILED, project=project, task=task, to_developer=True, message=msg
                )
            db.commit()
        except ApiError:
            db.rollback()
            log.exception("test outcome for task %s could not be applied", task_id)
            return
    if rework_feedback is not None:
        run_generation(rt, task_id, feedback=rework_feedback)


# -- deployment (FR-9) ----------------------------------------------------------------------------------------------
def deploy_task(rt: Runtime, db: Session, task: Task, user: User, environment: str | None) -> DeployOutcome:
    """Authorised deployment (UC-07). Synchronous: the outcome is part of the response."""
    actor = workflow.Actor(user=user)
    pipeline = load_pipeline(task.project.pipeline_config)
    workflow.check_event(db, task, "authorise_deployment", actor, pipeline)  # raises on any violation
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
