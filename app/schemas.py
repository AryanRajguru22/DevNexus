"""Pydantic request/response schemas (docs/TEAM_CONTRACT.md section 5). SHARED FILE (owner: Aryan)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator

from .enums import (
    AgentType,
    DeploymentStatus,
    Environment,
    NotificationKind,
    Priority,
    RequirementStatus,
    RequirementType,
)

# UTC timestamps are stored naive and serialised with a trailing "Z".
def _utc_z(d: datetime) -> str:
    return d.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


UTCDateTime = Annotated[datetime, PlainSerializer(_utc_z, return_type=str)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _nonblank(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("must not be blank")
    return v


# -- users / agents ---------------------------------------------------------------------------------------------
class UserOut(ORM):
    user_id: int
    name: str
    email: str
    role: str


class AgentOut(ORM):
    agent_id: int
    type: str
    status: str


# -- projects / requirements ------------------------------------------------------------------------------------
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    problem_statement: str = Field(min_length=1, max_length=2000)
    scope: str = Field(min_length=1, max_length=2000)
    objectives: str = Field(min_length=1, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None

    _strip = field_validator("name", "problem_statement", "scope", "objectives")(_nonblank)

    @model_validator(mode="after")
    def _dates_ordered(self) -> "ProjectCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class ProjectOut(ORM):
    project_id: int
    name: str
    status: str
    start_date: date | None
    end_date: date | None
    manager_id: int
    pipeline_config: dict[str, Any]
    problem_statement: str
    scope: str
    objectives: str
    task_count: int = 0
    requirement_count: int = 0


class RequirementCreate(BaseModel):
    description: str = Field(min_length=5, max_length=2000)
    type: RequirementType
    priority: Priority
    status: RequirementStatus = RequirementStatus.DRAFT

    _strip = field_validator("description")(_nonblank)

    @field_validator("description")
    @classmethod
    def _min_len_after_strip(cls, v: str) -> str:
        if len(v) < 5:
            raise ValueError("description must have at least 5 characters")
        return v


class RequirementOut(ORM):
    req_id: int
    project_id: int
    description: str
    type: str
    priority: str
    status: str


# -- tasks ------------------------------------------------------------------------------------------------------
class TaskCreate(BaseModel):
    project_id: int
    req_id: int
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)

    _strip = field_validator("title")(_nonblank)

    @field_validator("title")
    @classmethod
    def _single_line(cls, v: str) -> str:
        if "\n" in v or "\r" in v:
            raise ValueError("title must be a single line")
        return v


class AssignBody(BaseModel):
    agent_type: AgentType = AgentType.CODE_GENERATION


class ApproveBody(BaseModel):
    comments: str | None = Field(default=None, max_length=2000)


class RejectBody(BaseModel):
    comments: str = Field(min_length=1, max_length=2000)

    _strip = field_validator("comments")(_nonblank)


class DeployBody(BaseModel):
    environment: Environment | None = None


class TaskOut(ORM):
    task_id: int
    project_id: int
    req_id: int
    developer_id: int
    title: str
    description: str
    status: str
    status_group: str
    created_at: UTCDateTime
    status_changed_at: UTCDateTime
    run_count: int = 0


class AgentRunOut(ORM):
    run_id: int
    task_id: int
    agent_id: int
    branch_name: str
    started_at: UTCDateTime
    finished_at: UTCDateTime | None
    status: str
    error_message: str | None


class TestResultOut(ORM):
    __test__ = False

    test_id: int
    run_id: int
    passed_count: int
    failed_count: int
    coverage_pct: float
    simulated: bool
    created_at: UTCDateTime


class DeploymentOut(ORM):
    deploy_id: int
    run_id: int
    environment: str
    status: str
    deployed_at: UTCDateTime


class AuditEntryOut(ORM):
    log_id: int
    user_id: int | None
    agent_id: int | None
    actor_name: str
    action: str
    target_ref: str
    detail: str | None
    timestamp: UTCDateTime


class TaskDetail(TaskOut):
    runs: list[AgentRunOut]
    test_results: list[TestResultOut]
    deployments: list[DeploymentOut]
    history: list[AuditEntryOut]
    allowed_actions: list[str]
    retry_limit: int
    rework_allowed: bool


class DeployOutcome(BaseModel):
    outcome: Literal["succeeded", "failed"]
    message: str
    deployment: DeploymentOut
    task: TaskOut


class DiffFile(BaseModel):
    path: str
    diff: str


class DiffOut(BaseModel):
    branch: str
    base: str = "main"
    files: list[DiffFile]


# -- notifications ----------------------------------------------------------------------------------------------
class NotificationOut(ORM):
    notification_id: int
    user_id: int
    project_id: int
    task_id: int | None
    kind: NotificationKind
    message: str
    created_at: UTCDateTime
    is_read: bool


# -- analytics --------------------------------------------------------------------------------------------------
class RiskItem(BaseModel):
    category: str
    description: str
    probability: int
    impact: int
    score: int
    level: str
    task_ids: list[int] = []


class RiskAssessment(BaseModel):
    level: str
    score: int
    items: list[RiskItem]


class RiskReportOut(BaseModel):
    report_id: int
    project_id: int
    risk_level: str
    generated_at: UTCDateTime
    details: dict[str, Any]


class SprintVelocity(BaseModel):
    sprint_start: date
    sprint_end: date
    deployed: int


class CoverageOut(BaseModel):
    average_pct: float | None
    tasks_with_results: int
    simulated: bool = True


class Dashboard(BaseModel):
    project_id: int | None
    totals: dict[str, Any]
    progress_pct: float
    velocity: list[SprintVelocity]
    coverage: CoverageOut
    risk: RiskAssessment
    latest_risk_report: RiskReportOut | None
    generated_at: UTCDateTime


class Estimation(BaseModel):
    project_id: int | None
    task_count: int
    loc_actual: int
    loc_planned: int
    loc_total: int
    kloc: float
    effort_person_months: float
    duration_months: float
    team_size: float
    cost_inr: float
    model: str
    constants: dict[str, float]
    phase2_baseline: dict[str, Any]
    generated_at: UTCDateTime
