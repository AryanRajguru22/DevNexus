"""Notification service (FR-13). Recipient rules: docs/TEAM_CONTRACT.md section 8."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .enums import NotificationKind
from .models import Notification, Project, Task


def notify(
    db: Session,
    *,
    kind: NotificationKind,
    message: str,
    project: Project,
    task: Task | None,
    to_developer: bool = False,
    to_manager: bool = False,
) -> list[Notification]:
    recipients: list[int] = []
    if to_developer and task is not None:
        recipients.append(task.developer_id)
    if to_manager and project.manager_id not in recipients:
        recipients.append(project.manager_id)
    created = [
        Notification(
            user_id=uid,
            project_id=project.project_id,
            task_id=task.task_id if task else None,
            kind=kind.value,
            message=message,
        )
        for uid in recipients
    ]
    db.add_all(created)
    db.flush()
    return created
