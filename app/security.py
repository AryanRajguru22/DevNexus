"""Identity and role checks (NFR-3, NFR-11). SHARED FILE (owner: Aryan).

Deviation D-6: there is no login requirement (Phase 3 O-3), so the client sends X-User-Id and the role is read
from the USER row. A denied call is itself written to the audit log.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from . import audit
from .enums import Role
from .errors import forbidden, not_authenticated
from .models import User


def get_db(request: Request) -> Iterator[Session]:
    db = request.app.state.runtime.session_factory()
    try:
        yield db
    finally:
        db.close()


def current_user(db: Session = Depends(get_db), x_user_id: str | None = Header(default=None)) -> User:
    if not x_user_id or not x_user_id.isdigit():
        raise not_authenticated()
    user = db.get(User, int(x_user_id))
    if user is None:
        raise not_authenticated()
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    allowed = {r.value for r in roles}

    def dependency(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
        if user.role not in allowed:
            audit.record(
                db,
                user=user,
                action="access.denied",
                target_ref=f"endpoint:{request.url.path}",
                detail=f"{request.method} refused: role '{user.role}' not in {sorted(allowed)}",
            )
            db.commit()
            raise forbidden(f"Role '{user.role}' may not perform this action (needs one of: {', '.join(sorted(allowed))})")
        return user

    return dependency
