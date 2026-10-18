"""Project & Requirement Service endpoints (FR-1, FR-2, FR-3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..enums import ProjectStatus, Role
from ..errors import not_found
from ..models import Project, Requirement, Task, User
from ..schemas import ProjectCreate, ProjectOut, RequirementCreate, RequirementOut
from ..security import current_user, get_db, require_roles
from ..validation import PipelineConfig, default_pipeline

router = APIRouter(prefix="/api", tags=["projects"])


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise not_found(f"Project {project_id}")
    return project


def project_out(db: Session, project: Project) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    out.task_count = db.scalar(select(func.count()).select_from(Task).where(Task.project_id == project.project_id)) or 0
    out.requirement_count = (
        db.scalar(select(func.count()).select_from(Requirement).where(Requirement.project_id == project.project_id)) or 0
    )
    return out


@router.post("/projects", status_code=201, response_model=ProjectOut)
def create_project(
    body: ProjectCreate, user: User = Depends(require_roles(Role.PROJECT_MANAGER)), db: Session = Depends(get_db)
) -> ProjectOut:
    project = Project(
        name=body.name, status=ProjectStatus.ACTIVE.value, start_date=body.start_date, end_date=body.end_date,
        manager_id=user.user_id, pipeline_config=default_pipeline(), problem_statement=body.problem_statement,
        scope=body.scope, objectives=body.objectives,
    )
    db.add(project)
    db.flush()
    audit.record(db, user=user, action="project.create", target_ref=f"project:{project.project_id}", detail=project.name)
    db.commit()
    return project_out(db, project)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(_: User = Depends(current_user), db: Session = Depends(get_db)) -> list[ProjectOut]:
    return [project_out(db, p) for p in db.scalars(select(Project).order_by(Project.project_id))]


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)) -> ProjectOut:
    return project_out(db, get_project_or_404(db, project_id))


@router.post("/projects/{project_id}/requirements", status_code=201, response_model=RequirementOut)
def add_requirement(
    project_id: int,
    body: RequirementCreate,
    user: User = Depends(require_roles(Role.PROJECT_MANAGER)),
    db: Session = Depends(get_db),
) -> Requirement:
    project = get_project_or_404(db, project_id)
    req = Requirement(
        project_id=project.project_id, description=body.description, type=body.type.value,
        priority=body.priority.value, status=body.status.value,
    )
    db.add(req)
    db.flush()
    audit.record(db, user=user, action="requirement.add", target_ref=f"requirement:{req.req_id}",
                 detail=f"{req.type}/{req.priority} in project {project.project_id}")
    db.commit()
    return req


@router.get("/projects/{project_id}/requirements", response_model=list[RequirementOut])
def list_requirements(project_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Requirement]:
    get_project_or_404(db, project_id)
    return list(db.scalars(select(Requirement).where(Requirement.project_id == project_id).order_by(Requirement.req_id)))


@router.put("/projects/{project_id}/pipeline", response_model=ProjectOut)
def configure_pipeline(
    project_id: int,
    body: PipelineConfig,
    user: User = Depends(require_roles(Role.PROJECT_MANAGER)),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = get_project_or_404(db, project_id)
    project.pipeline_config = body.to_json()
    audit.record(db, user=user, action="pipeline.configure", target_ref=f"project:{project.project_id}",
                 detail=f"active={[a.value for a in body.active_agents]} retry_limit={body.retry_limit}")
    db.commit()
    return project_out(db, project)
