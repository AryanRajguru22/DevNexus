"""Exact enumeration strings from docs/TEAM_CONTRACT.md section 2."""
from enum import StrEnum


class Role(StrEnum):
    PROJECT_MANAGER = "project_manager"
    DEVELOPER = "developer"


class AgentType(StrEnum):
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class TaskStatus(StrEnum):
    """The 8 states of the Task state chart (Phase 3, Fig 3.7). Do not add states."""

    CREATED = "Created"
    ASSIGNED = "Assigned"
    GENERATING = "Generating"
    IN_REVIEW = "In Review"
    TESTING = "Testing"
    READY_FOR_DEPLOYMENT = "Ready for Deployment"
    DEPLOYED = "Deployed"
    FAILED = "Failed"


class StatusGroup(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# FR-6 vocabulary (queued / in-progress / completed / failed) mapped onto the 8 states.
STATUS_GROUP: dict[TaskStatus, StatusGroup] = {
    TaskStatus.CREATED: StatusGroup.QUEUED,
    TaskStatus.ASSIGNED: StatusGroup.QUEUED,
    TaskStatus.GENERATING: StatusGroup.IN_PROGRESS,
    TaskStatus.IN_REVIEW: StatusGroup.IN_PROGRESS,
    TaskStatus.TESTING: StatusGroup.IN_PROGRESS,
    TaskStatus.READY_FOR_DEPLOYMENT: StatusGroup.IN_PROGRESS,
    TaskStatus.DEPLOYED: StatusGroup.COMPLETED,
    TaskStatus.FAILED: StatusGroup.FAILED,
}


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DeploymentStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Environment(StrEnum):
    STAGING = "staging"
    PRODUCTION = "production"


class RiskLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class RequirementType(StrEnum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non-functional"


class Priority(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RequirementStatus(StrEnum):
    DRAFT = "Draft"
    APPROVED = "Approved"


class ProjectStatus(StrEnum):
    PLANNING = "Planning"
    ACTIVE = "Active"
    COMPLETED = "Completed"


class NotificationKind(StrEnum):
    CODE_READY = "code_ready"
    TASK_FAILED = "task_failed"
    TESTS_PASSED = "tests_passed"
    TESTS_FAILED = "tests_failed"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"
    RISK_THRESHOLD = "risk_threshold"


def sql_in(enum_cls: type[StrEnum]) -> str:
    """Render the values of an enum as a SQL IN (...) list for CHECK constraints."""
    return ", ".join(f"'{m.value}'" for m in enum_cls)
