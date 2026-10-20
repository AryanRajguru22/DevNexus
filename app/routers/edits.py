"""Edit endpoints for requirements and projects (contract C-3, proposed extension E-5; task PLAN-08).

No FR requires editing: FR-2 only says "capture and store". These endpoints exist so a PM can fix mistakes and
approve requirements. Rules:
- Only a project_manager may edit (others get 403, audited as access.denied by require_roles).
- A requirement's content may change only while it is Draft; its status may move Draft -> Approved only.
  An Approved requirement is locked: any value that differs from the stored one is refused with
  422 requirement_locked. Re-sending the stored value is a no-op, so a client can safely re-submit a form.
- Project dates are checked after merging the body with the stored values. Pipeline config is not editable here
  (use PUT /api/projects/{id}/pipeline). Unknown fields are rejected (extra="forbid").
Models live in this file so the shared app/schemas.py stays untouched.
"""
from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from .. import audit
from ..enums import Priority, ProjectStatus, RequirementStatus, RequirementType, Role
from ..errors import ApiError, not_found, validation_error
from ..models import Requirement, User
from ..schemas import ProjectOut, RequirementOut
from ..security import get_db, require_roles
from .projects import get_project_or_404, project_out

router = APIRouter(prefix="/api", tags=["edits"])

# Fields that may be omitted but must not be sent as null (the column is NOT NULL).
_NOT_NULL_REQ = ("description", "type", "priority", "status")
_NOT_NULL_PROJECT = ("name", "problem_statement", "scope", "objectives", "status")


def _strip_nonblank(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not v:
        raise ValueError("must not be blank")
    return v


class _Patch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    not_null: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _at_least_one_and_no_nulls(self) -> "_Patch":
        if not self.model_fields_set:
            raise ValueError("send at least one field to change")
        for name in self.not_null:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self

    def changes(self) -> dict[str, Any]:
        """Only the fields the client actually sent, enums as plain strings."""
        out = {}
        for name in self.model_fields_set:
            value = getattr(self, name)
            out[name] = value.value if hasattr(value, "value") else value
        return out


class RequirementPatch(_Patch):
    not_null: ClassVar[tuple[str, ...]] = _NOT_NULL_REQ
    description: str | None = Field(default=None, min_length=5, max_length=2000)
    type: RequirementType | None = None
    priority: Priority | None = None
    status: RequirementStatus | None = None

    @field_validator("description")
    @classmethod
    def _desc(cls, v: str | None) -> str | None:
        v = _strip_nonblank(v)
        if v is not None and len(v) < 5:
            raise ValueError("description must have at least 5 characters")
        return v


class ProjectPatch(_Patch):
    not_null: ClassVar[tuple[str, ...]] = _NOT_NULL_PROJECT
    name: str | None = Field(default=None, min_length=1, max_length=120)
    problem_statement: str | None = Field(default=None, min_length=1, max_length=2000)
    scope: str | None = Field(default=None, min_length=1, max_length=2000)
    objectives: str | None = Field(default=None, min_length=1, max_length=2000)
    start_date: date | None = None  # null clears the date
    end_date: date | None = None
    status: ProjectStatus | None = None

    _strip = field_validator("name", "problem_statement", "scope", "objectives")(_strip_nonblank)


def _locked(req: Requirement, changed: list[str]) -> ApiError:
    return ApiError(
        422, "requirement_locked",
        f"Requirement {req.req_id} is Approved and locked; it cannot change ({', '.join(changed)})",
        {"req_id": req.req_id, "fields": changed},
    )


@router.patch("/requirements/{req_id}", response_model=RequirementOut)
def edit_requirement(
    req_id: int,
    body: RequirementPatch,
    user: User = Depends(require_roles(Role.PROJECT_MANAGER)),
    db: Session = Depends(get_db),
) -> Requirement:
    req = db.get(Requirement, req_id)
    if req is None:
        raise not_found(f"Requirement {req_id}")
    changed = {k: v for k, v in body.changes().items() if getattr(req, k) != v}
    if req.status == RequirementStatus.APPROVED.value and changed:
        raise _locked(req, sorted(changed))
    for name, value in changed.items():
        setattr(req, name, value)
    audit.record(db, user=user, action="requirement.update", target_ref=f"requirement:{req.req_id}",
                 detail=_describe(changed))
    db.commit()
    return req


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def edit_project(
    project_id: int,
    body: ProjectPatch,
    user: User = Depends(require_roles(Role.PROJECT_MANAGER)),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = get_project_or_404(db, project_id)
    changed = {k: v for k, v in body.changes().items() if getattr(project, k) != v}
    start = changed.get("start_date", project.start_date)
    end = changed.get("end_date", project.end_date)
    if start and end and end < start:
        raise validation_error(
            "end_date must not be before start_date",
            details=[{"field": "end_date", "message": f"{end.isoformat()} is before start_date {start.isoformat()}"}],
        )
    for name, value in changed.items():
        setattr(project, name, value)
    audit.record(db, user=user, action="project.update", target_ref=f"project:{project.project_id}",
                 detail=_describe(changed))
    db.commit()
    return project_out(db, project)


def _describe(changed: dict[str, Any]) -> str:
    if not changed:
        return "no changes (values already stored)"
    shown = []
    for name, value in sorted(changed.items()):
        text = "null" if value is None else str(value)
        shown.append(f"{name}={text[:60] + '…' if len(text) > 60 else text}")
    return "changed: " + "; ".join(shown)
