"""Identity, agents, notifications and audit-trail endpoints (FR-13, FR-14)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import not_found
from ..models import Agent, AuditLog, Notification, User
from ..schemas import AgentOut, AuditEntryOut, NotificationOut, UserOut
from ..security import current_user, get_db
from ..services.tasks import audit_out

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """Unauthenticated on purpose: it feeds the demo user switcher (deviation D-6)."""
    return list(db.scalars(select(User).order_by(User.user_id)))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/agents", response_model=list[AgentOut])
def list_agents(_: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Agent]:
    return list(db.scalars(select(Agent).order_by(Agent.agent_id)))


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user.user_id).order_by(Notification.notification_id.desc())
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return list(db.scalars(stmt.limit(200)))


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Notification:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.user_id:  # other users' notifications are not revealed
        raise not_found(f"Notification {notification_id}")
    note.is_read = True
    db.commit()
    return note


@router.get("/audit", response_model=list[AuditEntryOut])
def search_audit(
    action: str | None = None,
    target_ref: str | None = None,
    user_id: int | None = None,
    agent_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[AuditEntryOut]:
    stmt = select(AuditLog).order_by(AuditLog.log_id.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if target_ref:
        stmt = stmt.where(AuditLog.target_ref == target_ref)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if agent_id is not None:
        stmt = stmt.where(AuditLog.agent_id == agent_id)
    return [audit_out(e) for e in db.scalars(stmt.limit(limit))]
