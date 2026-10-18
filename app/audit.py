"""Append-only audit trail helper (FR-14, NFR-11). Rows are written in the caller's transaction."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .models import Agent, AuditLog, User


def record(
    db: Session,
    *,
    action: str,
    target_ref: str,
    user: User | None = None,
    agent: Agent | None = None,
    detail: str | None = None,
) -> AuditLog:
    if (user is None) == (agent is None):
        raise ValueError("an audit entry needs exactly one actor (user or agent)")
    entry = AuditLog(
        user_id=user.user_id if user else None,
        agent_id=agent.agent_id if agent else None,
        action=action,
        target_ref=target_ref[:60],
        detail=detail,
    )
    db.add(entry)
    db.flush()
    return entry
