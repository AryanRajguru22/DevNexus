"""Task endpoints: lifecycle actions of the Task state chart (FR-4..FR-9)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit, workflow
from ..enums import AgentType, Role, StatusGroup, TaskStatus, STATUS_GROUP
from ..errors import ApiError, agent_inactive, invalid_transition, not_found, validation_error
from ..models import AgentRun, AuditLog, Deployment, Requirement, Task, TestResult, User
from ..schemas import (
    ApproveBody, AssignBody, DeployBody, DeployOutcome, DiffOut, RejectBody, TaskCreate, TaskDetail, TaskOut,
    AgentRunOut, DeploymentOut, TestResultOut,
)
from ..security import current_user, get_db, require_roles
from ..services import orchestrator
from ..services.runtime import Runtime
from ..services.tasks import audit_out, fire, task_out
from ..validation import load_pipeline
from .projects import get_project_or_404

router = APIRouter(prefix="/api", tags=["tasks"])


def runtime(request: Request) -> Runtime:
    return request.app.state.runtime


def get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise not_found(f"Task {task_id}")
    return task


@router.post("/tasks", status_code=201, response_model=TaskOut)
def create_task(
    body: TaskCreate, user: User = Depends(require_roles(Role.DEVELOPER)), db: Session = Depends(get_db)
) -> TaskOut:
    project = get_project_or_404(db, body.project_id)
    requirement = db.get(Requirement, body.req_id)
    if requirement is None:
        raise not_found(f"Requirement {body.req_id}")
    if requirement.project_id != project.project_id:
        raise validation_error(
            f"Requirement {body.req_id} belongs to project {requirement.project_id}, not {project.project_id}",
            code="requirement_project_mismatch",
        )
    task = Task(
        project_id=project.project_id, req_id=requirement.req_id, developer_id=user.user_id,
        title=body.title, description=body.description, status=TaskStatus.CREATED.value,
    )
    db.add(task)
    db.flush()
    audit.record(db, user=user, action="task.create", target_ref=f"task:{task.task_id}",
                 detail=f"from requirement:{requirement.req_id}")
    db.commit()
    return task_out(db, task)


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    project_id: int | None = None,
    status: TaskStatus | None = None,
    status_group: StatusGroup | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    stmt = select(Task).order_by(Task.task_id)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Task.status == status.value)
    tasks = list(db.scalars(stmt))
    if status_group is not None:
        tasks = [t for t in tasks if STATUS_GROUP[TaskStatus(t.status)] == status_group]
    return [task_out(db, t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> TaskDetail:
    task = get_task_or_404(db, task_id)
    pipeline = load_pipeline(task.project.pipeline_config)
    run_ids = [r.run_id for r in task.runs]
    tests = list(db.scalars(select(TestResult).where(TestResult.run_id.in_(run_ids)).order_by(TestResult.test_id))) if run_ids else []
    deployments = list(db.scalars(select(Deployment).where(Deployment.run_id.in_(run_ids)).order_by(Deployment.deploy_id))) if run_ids else []
    refs = [f"task:{task.task_id}"] + [f"deployment:{d.deploy_id}" for d in deployments]
    history = list(db.scalars(select(AuditLog).where(AuditLog.target_ref.in_(refs)).order_by(AuditLog.log_id)))
    base = task_out(db, task)
    return TaskDetail(
        **base.model_dump(),
        runs=[AgentRunOut.model_validate(r) for r in task.runs],
        test_results=[TestResultOut.model_validate(t) for t in tests],
        deployments=[DeploymentOut.model_validate(d) for d in deployments],
        history=[audit_out(h) for h in history],
        allowed_actions=workflow.available_actions(db, task, user),
        retry_limit=pipeline.retry_limit,
        rework_allowed=workflow.rework_allowed(db, task, pipeline),
    )


@router.get("/tasks/{task_id}/diff", response_model=DiffOut)
def task_diff(
    task_id: int, request: Request, _: User = Depends(current_user), db: Session = Depends(get_db)
) -> DiffOut:
    task = get_task_or_404(db, task_id)
    if not task.runs:
        raise ApiError(409, "precondition_failed", "No code has been generated for this task yet")
    branch = task.runs[-1].branch_name
    return DiffOut(branch=branch, files=runtime(request).git.diff(task.project_id, branch))


@router.post("/tasks/{task_id}/assign", response_model=TaskOut)
def assign_task(
    task_id: int,
    request: Request,
    background: BackgroundTasks,
    body: AssignBody | None = None,
    user: User = Depends(require_roles(Role.DEVELOPER)),
    db: Session = Depends(get_db),
) -> TaskOut:
    body = body or AssignBody()
    if body.agent_type != AgentType.CODE_GENERATION:
        raise validation_error(
            "Only the code_generation agent can be assigned a task; testing and deployment are triggered by the "
            "review and deployment gates", code="agent_not_assignable",
        )
    task = get_task_or_404(db, task_id)
    fire(db, task, "assign", workflow.Actor(user=user), detail=f"assigned to {body.agent_type.value} agent")
    db.commit()
    background.add_task(orchestrator.run_generation, runtime(request), task.task_id)
    return task_out(db, task)


@router.post("/tasks/{task_id}/approve", response_model=TaskOut)
def approve_task(
    task_id: int,
    request: Request,
    background: BackgroundTasks,
    body: ApproveBody | None = None,
    user: User = Depends(require_roles(Role.DEVELOPER)),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = get_task_or_404(db, task_id)
    fire(db, task, "approve", workflow.Actor(user=user), detail=(body.comments if body else None) or "approved")
    db.commit()
    background.add_task(orchestrator.run_tests, runtime(request), task.task_id)
    return task_out(db, task)


@router.post("/tasks/{task_id}/reject", response_model=TaskOut)
def reject_task(
    task_id: int,
    body: RejectBody,
    request: Request,
    background: BackgroundTasks,
    user: User = Depends(require_roles(Role.DEVELOPER)),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = get_task_or_404(db, task_id)
    fire(db, task, "reject", workflow.Actor(user=user), detail=body.comments)
    db.commit()
    background.add_task(orchestrator.run_generation, runtime(request), task.task_id, body.comments)
    return task_out(db, task)


@router.post("/tasks/{task_id}/retry", response_model=TaskOut)
def retry_task(
    task_id: int,
    request: Request,
    background: BackgroundTasks,
    user: User = Depends(require_roles(Role.DEVELOPER)),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = get_task_or_404(db, task_id)
    fire(db, task, "retry", workflow.Actor(user=user), detail="retry after agent failure")
    db.commit()
    background.add_task(orchestrator.run_generation, runtime(request), task.task_id)
    return task_out(db, task)


@router.post("/tasks/{task_id}/tests", response_model=TaskOut)
def rerun_tests(
    task_id: int,
    request: Request,
    background: BackgroundTasks,
    user: User = Depends(require_roles(Role.DEVELOPER)),
    db: Session = Depends(get_db),
) -> TaskOut:
    """Re-run the automated tests (UC-06). Approval already starts them; this is for a task still in Testing."""
    task = get_task_or_404(db, task_id)
    if task.status != TaskStatus.TESTING.value:
        raise invalid_transition(
            f"Task is '{task.status}'; tests can only be re-run in 'Testing'",
            current=task.status, required=TaskStatus.TESTING.value, event="tests",
        )
    if not load_pipeline(task.project.pipeline_config).is_active(AgentType.TESTING):
        raise agent_inactive(AgentType.TESTING.value)
    audit.record(db, user=user, action="task.tests_rerun", target_ref=f"task:{task.task_id}", detail="re-run requested")
    db.commit()
    background.add_task(orchestrator.run_tests, runtime(request), task.task_id)
    return task_out(db, task)


@router.post("/tasks/{task_id}/deploy", response_model=DeployOutcome)
def deploy_task(
    task_id: int,
    request: Request,
    body: DeployBody | None = None,
    user: User = Depends(require_roles(Role.DEVELOPER, Role.PROJECT_MANAGER)),
    db: Session = Depends(get_db),
) -> DeployOutcome:
    task = get_task_or_404(db, task_id)
    env = body.environment.value if body and body.environment else None
    return orchestrator.deploy_task(runtime(request), db, task, user, env)
