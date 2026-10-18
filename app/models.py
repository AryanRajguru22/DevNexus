"""SQLAlchemy models: the 10 entities of the Phase 3 E-R diagram (Fig 3.6, section 14.3) plus NOTIFICATION.

Columns marked "extension" are additions documented in docs/TEAM_CONTRACT.md section 3.
SHARED FILE - change only via pull request reviewed by Aryan.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DDL,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .enums import (
    AgentType,
    DeploymentStatus,
    Environment,
    NotificationKind,
    Priority,
    ProjectStatus,
    RequirementStatus,
    RequirementType,
    Role,
    RiskLevel,
    RunStatus,
    TaskStatus,
    sql_in,
)


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite has no timezone type; the API adds the trailing 'Z')."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    __table_args__ = (CheckConstraint(f"role IN ({sql_in(Role)})", name="ck_user_role"),)

    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    role: Mapped[str] = mapped_column(String(20))


class Project(Base):
    __tablename__ = "project"
    __table_args__ = (CheckConstraint(f"status IN ({sql_in(ProjectStatus)})", name="ck_project_status"),)

    project_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.ACTIVE.value)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    pipeline_config: Mapped[dict[str, Any]] = mapped_column(JSON)
    # extension E-1 (FR-1 asks for these three fields)
    problem_statement: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(Text, default="")
    objectives: Mapped[str] = mapped_column(Text, default="")

    requirements: Mapped[list["Requirement"]] = relationship(back_populates="project")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")


class Requirement(Base):
    __tablename__ = "requirement"
    __table_args__ = (
        CheckConstraint(f"type IN ({sql_in(RequirementType)})", name="ck_requirement_type"),
        CheckConstraint(f"priority IN ({sql_in(Priority)})", name="ck_requirement_priority"),
        CheckConstraint(f"status IN ({sql_in(RequirementStatus)})", name="ck_requirement_status"),
    )

    req_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.project_id"))
    description: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20))
    priority: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10), default=RequirementStatus.DRAFT.value)

    project: Mapped[Project] = relationship(back_populates="requirements")


class Task(Base):
    __tablename__ = "task"
    __table_args__ = (CheckConstraint(f"status IN ({sql_in(TaskStatus)})", name="ck_task_status"),)

    task_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.project_id"))
    req_id: Mapped[int] = mapped_column(ForeignKey("requirement.req_id"))
    developer_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(25), default=TaskStatus.CREATED.value)
    # extension E-2
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status_changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="tasks")
    requirement: Mapped[Requirement] = relationship()
    developer: Mapped[User] = relationship()
    runs: Mapped[list["AgentRun"]] = relationship(back_populates="task", order_by="AgentRun.run_id")


class Agent(Base):
    __tablename__ = "agent"
    __table_args__ = (CheckConstraint(f"type IN ({sql_in(AgentType)})", name="ck_agent_type"),)

    agent_id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(20), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="available")


class AgentRun(Base):
    __tablename__ = "agent_run"
    __table_args__ = (CheckConstraint(f"status IN ({sql_in(RunStatus)})", name="ck_agent_run_status"),)

    run_id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task.task_id"))
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent.agent_id"))
    branch_name: Mapped[str] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[str] = mapped_column(String(10), default=RunStatus.RUNNING.value)
    # extension E-2
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[Task] = relationship(back_populates="runs")


class TestResult(Base):
    __test__ = False  # not a pytest class
    __tablename__ = "test_result"

    test_id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_run.run_id"))
    passed_count: Mapped[int] = mapped_column(Integer)
    failed_count: Mapped[int] = mapped_column(Integer)
    coverage_pct: Mapped[float] = mapped_column(Float)
    # extension E-2
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)


class Deployment(Base):
    __tablename__ = "deployment"
    __table_args__ = (
        CheckConstraint(f"status IN ({sql_in(DeploymentStatus)})", name="ck_deployment_status"),
        CheckConstraint(f"environment IN ({sql_in(Environment)})", name="ck_deployment_env"),
    )

    deploy_id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_run.run_id"))
    environment: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(10))
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RiskReport(Base):
    __tablename__ = "risk_report"
    __table_args__ = (CheckConstraint(f"risk_level IN ({sql_in(RiskLevel)})", name="ck_risk_level"),)

    report_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.project_id"))
    risk_level: Mapped[str] = mapped_column(String(10))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # extension E-2: delayed tasks, repeated failures, slippage (FR-11)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AuditLog(Base):
    """Append-only (Phase 3 section 14.3): triggers below reject UPDATE and DELETE."""

    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND agent_id IS NULL) OR (user_id IS NULL AND agent_id IS NOT NULL)",
            name="ck_audit_log_exactly_one_actor",
        ),
    )

    log_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.user_id"), nullable=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agent.agent_id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    target_ref: Mapped[str] = mapped_column(String(60))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # extension E-2

    user: Mapped[User | None] = relationship()
    agent: Mapped[Agent | None] = relationship()


event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log "
        "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END"
    ),
)
event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON audit_log "
        "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END"
    ),
)


class Notification(Base):
    """Extension E-3: FR-13 needs recipient-specific alerts; the Phase 3 E-R has no such entity."""

    __tablename__ = "notification"
    __table_args__ = (CheckConstraint(f"kind IN ({sql_in(NotificationKind)})", name="ck_notification_kind"),)

    notification_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("project.project_id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("task.task_id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
