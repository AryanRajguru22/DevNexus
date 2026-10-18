"""Task workflow engine - the single source of state rules (Phase 3 Fig 3.7, docs/TEAM_CONTRACT.md section 4).

Owner: Member B. SHARED FILE: the TRANSITIONS table is frozen except through a contract change.

Rules enforced here, and nowhere else:
* only the 8 documented states; only the documented (state, event) pairs;
* who may fire an event (role or agent type);
* the agent type needed must be active in the project's pipeline (UC-03 alt 3a);
* rework / retry events are bounded by pipeline_config.retry_limit (A-2) - refused, never a new state;
* the state change and its audit row are written in the caller's transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import audit
from .enums import AgentType, Role, TaskStatus
from .errors import (
    ApiError,
    agent_inactive,
    forbidden,
    invalid_transition,
    retry_limit_exceeded,
)
from .models import Agent, AgentRun, Task, User, utcnow
from .validation import PipelineConfig, load_pipeline

DEV = Role.DEVELOPER.value
PM = Role.PROJECT_MANAGER.value
AGENT_CODEGEN = f"agent:{AgentType.CODE_GENERATION.value}"
AGENT_TESTING = f"agent:{AgentType.TESTING.value}"


@dataclass(frozen=True)
class Actor:
    """Who fires an event: a User (human) or an Agent (system actor)."""

    user: User | None = None
    agent: Agent | None = None

    @property
    def key(self) -> str:
        if self.user is not None:
            return self.user.role
        if self.agent is not None:
            return f"agent:{self.agent.type}"
        raise ValueError("actor has neither user nor agent")


@dataclass(frozen=True)
class Transition:
    event: str
    src: TaskStatus
    dst: TaskStatus
    actors: frozenset[str]
    audit_action: str
    needs_agent: AgentType | None = None  # must be active in the pipeline
    rework: bool = False  # bounded by retry_limit


S = TaskStatus
_CG = AgentType.CODE_GENERATION

TRANSITIONS: dict[str, Transition] = {
    t.event: t
    for t in [
        Transition("assign", S.CREATED, S.ASSIGNED, frozenset({DEV}), "task.assign", needs_agent=_CG),
        Transition("agent_start", S.ASSIGNED, S.GENERATING, frozenset({AGENT_CODEGEN}), "agent.start"),
        Transition("code_ready", S.GENERATING, S.IN_REVIEW, frozenset({AGENT_CODEGEN}), "agent.generate"),
        Transition("agent_error", S.GENERATING, S.FAILED, frozenset({AGENT_CODEGEN}), "agent.error"),
        Transition("approve", S.IN_REVIEW, S.TESTING, frozenset({DEV}), "task.approve", needs_agent=AgentType.TESTING),
        Transition("reject", S.IN_REVIEW, S.GENERATING, frozenset({DEV}), "task.reject", needs_agent=_CG, rework=True),
        Transition("tests_passed", S.TESTING, S.READY_FOR_DEPLOYMENT, frozenset({AGENT_TESTING}), "agent.test"),
        Transition(
            "tests_failed", S.TESTING, S.GENERATING, frozenset({AGENT_TESTING}), "agent.test",
            needs_agent=_CG, rework=True,
        ),
        Transition(
            "authorise_deployment", S.READY_FOR_DEPLOYMENT, S.DEPLOYED, frozenset({DEV, PM}),
            "task.deploy_authorise", needs_agent=AgentType.DEPLOYMENT,
        ),
        Transition("retry", S.FAILED, S.ASSIGNED, frozenset({DEV}), "task.retry", needs_agent=_CG, rework=True),
    ]
}

# User-facing action names (UI buttons / allowed_actions) -> workflow event.
USER_ACTIONS: dict[str, str] = {
    "assign": "assign",
    "approve": "approve",
    "reject": "reject",
    "retry": "retry",
    "deploy": "authorise_deployment",
}


def run_count(db: Session, task: Task) -> int:
    return db.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.task_id == task.task_id)) or 0


def rework_allowed(db: Session, task: Task, pipeline: PipelineConfig) -> bool:
    """The initial run is not a retry, so N runs have used N-1 reworks; allow while runs <= retry_limit."""
    return run_count(db, task) <= pipeline.retry_limit


def check_event(db: Session, task: Task, event: str, actor: Actor, pipeline: PipelineConfig | None = None) -> Transition:
    """Raise an ApiError if `event` may not fire now; otherwise return the transition. Changes nothing."""
    transition = TRANSITIONS.get(event)
    if transition is None:
        raise invalid_transition(f"Unknown workflow event '{event}'")
    if task.status != transition.src.value:
        raise invalid_transition(
            f"Task is '{task.status}'; '{event}' needs '{transition.src.value}'",
            current=task.status, required=transition.src.value, event=event,
        )
    if actor.key not in transition.actors:
        raise forbidden(f"'{actor.key}' may not fire '{event}' (allowed: {', '.join(sorted(transition.actors))})")
    pipeline = pipeline or load_pipeline(task.project.pipeline_config)
    if transition.needs_agent is not None and not pipeline.is_active(transition.needs_agent):
        raise agent_inactive(transition.needs_agent.value)
    if transition.rework and not rework_allowed(db, task, pipeline):
        raise retry_limit_exceeded(
            f"Retry limit ({pipeline.retry_limit}) reached for this task; '{event}' refused",
            retry_limit=pipeline.retry_limit, runs=run_count(db, task), event=event,
        )
    return transition


def apply_event(
    db: Session,
    task: Task,
    event: str,
    actor: Actor,
    *,
    detail: str | None = None,
    audit_entry: bool = True,
    now: datetime | None = None,
) -> Task:
    """Validate, move the task to its next state, and write the audit row (same transaction)."""
    transition = check_event(db, task, event, actor)
    task.status = transition.dst.value
    task.status_changed_at = now or utcnow()
    if audit_entry:
        audit.record(
            db,
            user=actor.user,
            agent=actor.agent,
            action=transition.audit_action,
            target_ref=f"task:{task.task_id}",
            detail=detail,
        )
    db.flush()
    return task


def available_actions(db: Session, task: Task, user: User) -> list[str]:
    """Actions the *current user* may take on the task right now (drives the UI buttons)."""
    actor = Actor(user=user)
    pipeline = load_pipeline(task.project.pipeline_config)
    actions: list[str] = []
    for name, event in USER_ACTIONS.items():
        try:
            check_event(db, task, event, actor, pipeline)
        except ApiError:
            continue
        actions.append(name)
    # Re-run of the automated tests (UC-06): valid while the task sits in Testing (e.g. after a failed run
    # that could not rework because of the retry limit).
    if task.status == TaskStatus.TESTING.value and user.role == DEV and pipeline.is_active(AgentType.TESTING):
        actions.append("tests")
    return actions
