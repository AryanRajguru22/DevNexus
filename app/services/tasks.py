"""Task helpers shared by the routers and the orchestrator: guarded transitions, DTO building."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit, notifications, workflow
from ..adapters.llm import slugify
from ..enums import STATUS_GROUP, NotificationKind, TaskStatus
from ..errors import ApiError
from ..models import Agent, AuditLog, Task
from ..schemas import AuditEntryOut, TaskOut
from . import analytics


def branch_for(task: Task) -> str:
    """Isolated feature branch for a task (NFR-6): feature/task-<id>-<slug>."""
    return f"feature/task-{task.task_id}-{slugify(task.title)[:30].replace('_', '-')}"


def get_agent(db: Session, agent_type: str) -> Agent:
    return db.scalars(select(Agent).where(Agent.type == agent_type)).one()


def hints_for(task: Task) -> str:
    """Text scanned by the mock adapters for demo failure markers."""
    return f"{task.title} {task.description}"


def flag_retry_limit(db: Session, task: Task, actor: workflow.Actor, err: ApiError) -> None:
    """Retry limit hit: record it, alert the PM and re-evaluate project risk (FR-11, FR-13). No state change."""
    audit.record(
        db, user=actor.user, agent=actor.agent, action="task.retry_limit_exceeded",
        target_ref=f"task:{task.task_id}", detail=err.message,
    )
    notifications.notify(
        db, kind=NotificationKind.RISK_THRESHOLD, project=task.project, task=task, to_manager=True,
        message=f"Task '{task.title}' reached the retry limit; it is reported as a risk.",
    )
    analytics.check_risk_threshold(db, task.project)


def fire(
    db: Session, task: Task, event: str, actor: workflow.Actor, *, detail: str | None = None, audit_entry: bool = True
) -> Task:
    """workflow.apply_event plus the retry-limit side effects, which must survive the refusal."""
    try:
        return workflow.apply_event(db, task, event, actor, detail=detail, audit_entry=audit_entry)
    except ApiError as err:
        if err.code == "retry_limit_exceeded":
            flag_retry_limit(db, task, actor, err)
            db.commit()
        raise


def task_out(db: Session, task: Task) -> TaskOut:
    data = TaskOut.model_validate(
        {
            **{c: getattr(task, c) for c in (
                "task_id", "project_id", "req_id", "developer_id", "title", "description", "status",
                "created_at", "status_changed_at")},
            "status_group": STATUS_GROUP[TaskStatus(task.status)].value,
            "run_count": workflow.run_count(db, task),
        }
    )
    return data


def audit_out(entry: AuditLog) -> AuditEntryOut:
    if entry.user is not None:
        actor = entry.user.name
    else:
        actor = f"{entry.agent.type.replace('_', ' ').title()} Agent" if entry.agent else "unknown"
    return AuditEntryOut(
        log_id=entry.log_id, user_id=entry.user_id, agent_id=entry.agent_id, actor_name=actor,
        action=entry.action, target_ref=entry.target_ref, detail=entry.detail, timestamp=entry.timestamp,
    )
