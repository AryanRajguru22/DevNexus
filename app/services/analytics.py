"""Analytics & Risk Service (FR-10, FR-11, FR-12). Rules: docs/TEAM_CONTRACT.md section 9.

Every figure is computed from persisted rows on each request (NFR-2). Nothing here is sample data.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..adapters.git_local import LocalGitAdapter
from ..enums import STATUS_GROUP, NotificationKind, RiskLevel, StatusGroup, TaskStatus
from ..models import AgentRun, AuditLog, Deployment, Project, RiskReport, Task, TestResult, utcnow
from .. import notifications
from ..validation import load_pipeline

SPRINT_DAYS = 14  # Lab 1: 2-week sprints
COCOMO_A, COCOMO_B, COCOMO_C, COCOMO_D = 2.4, 1.05, 2.5, 0.38  # Phase 2 section 5-6, organic mode
COST_PER_PERSON_MONTH_INR = 60_000  # Phase 2 section 7
HIGH_SCORE, MEDIUM_SCORE = 15, 9  # Phase 2 section 11
IMPACT = {"delayed_tasks": 3, "repeated_failures": 4, "schedule_slippage": 4}
SLIPPAGE_GAP = 0.20

PHASE2_BASELINE = {
    "source": "Phase 2 Estimation & Management, sections 3-7",
    "loc": 8000,
    "kloc": 8.0,
    "effort_person_months": 21.3,
    "duration_months": 8.0,
    "team_size": 2.7,
    "cost_inr": 1_278_000,
}


def level_for(score: int) -> str:
    if score >= HIGH_SCORE:
        return RiskLevel.HIGH.value
    if score >= MEDIUM_SCORE:
        return RiskLevel.MEDIUM.value
    return RiskLevel.LOW.value


def _tasks(db: Session, project_id: int | None) -> list[Task]:
    stmt = select(Task).order_by(Task.task_id)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    return list(db.scalars(stmt))


def basic_cocomo(kloc: float) -> tuple[float, float, float]:
    """(effort person-months, duration months, average team size) for the organic mode."""
    if kloc <= 0:
        return 0.0, 0.0, 0.0
    effort = COCOMO_A * kloc**COCOMO_B
    duration = COCOMO_C * effort**COCOMO_D
    return effort, duration, effort / duration


# -- FR-10 -------------------------------------------------------------------------------------------------------
def estimation(db: Session, git: LocalGitAdapter, project_id: int | None, now: datetime | None = None) -> dict:
    actual = planned = 0
    tasks = _tasks(db, project_id)
    for task in tasks:
        last_run = db.scalars(
            select(AgentRun).where(AgentRun.task_id == task.task_id).order_by(AgentRun.run_id.desc()).limit(1)
        ).first()
        if last_run is not None and last_run.status == "completed":
            actual += git.loc(task.project_id, last_run.branch_name)
        else:
            max_loc = load_pipeline(task.project.pipeline_config).constraints.max_loc
            planned += max_loc // 2
    total = actual + planned
    kloc = total / 1000
    effort, duration, team = basic_cocomo(kloc)
    return {
        "project_id": project_id,
        "task_count": len(tasks),
        "loc_actual": actual,
        "loc_planned": planned,
        "loc_total": total,
        "kloc": round(kloc, 3),
        "effort_person_months": round(effort, 2),
        "duration_months": round(duration, 2),
        "team_size": round(team, 2),
        "cost_inr": round(effort * COST_PER_PERSON_MONTH_INR, 2),
        "model": "Basic COCOMO, organic mode (Phase 2): E=2.4*KLOC^1.05, D=2.5*E^0.38, Rs 60,000 per person-month",
        "constants": {"a": COCOMO_A, "b": COCOMO_B, "c": COCOMO_C, "d": COCOMO_D,
                      "cost_per_person_month_inr": COST_PER_PERSON_MONTH_INR},
        "phase2_baseline": PHASE2_BASELINE,
        "generated_at": now or utcnow(),
    }


# -- FR-11 -------------------------------------------------------------------------------------------------------
def _item(category: str, description: str, probability: int, task_ids: list[int]) -> dict:
    probability = max(1, min(5, probability))
    impact = IMPACT[category]
    score = probability * impact
    return {
        "category": category,
        "description": description,
        "probability": probability,
        "impact": impact,
        "score": score,
        "level": level_for(score),
        "task_ids": task_ids,
    }


def assess_risk(db: Session, project_id: int, now: datetime | None = None) -> dict:
    now = now or utcnow()
    project = db.get(Project, project_id)
    pipeline = load_pipeline(project.pipeline_config)
    tasks = _tasks(db, project_id)
    items: list[dict] = []

    # Delayed tasks: open and idle in the same state for longer than the pipeline threshold.
    threshold = timedelta(hours=pipeline.constraints.delay_threshold_hours)
    delayed = [
        t.task_id for t in tasks
        if t.status != TaskStatus.DEPLOYED.value and now - t.status_changed_at > threshold
    ]
    if delayed:
        items.append(_item(
            "delayed_tasks",
            f"{len(delayed)} task(s) idle for more than {pipeline.constraints.delay_threshold_hours} h",
            1 + len(delayed), delayed,
        ))

    # Repeated agent failures: >= 2 failed runs/test results, or the retry limit was hit.
    repeated: list[int] = []
    for t in tasks:
        failed_runs = db.scalar(
            select(func.count()).select_from(AgentRun).where(AgentRun.task_id == t.task_id, AgentRun.status == "failed")
        ) or 0
        failed_tests = db.scalar(
            select(func.count()).select_from(TestResult).join(AgentRun, TestResult.run_id == AgentRun.run_id)
            .where(AgentRun.task_id == t.task_id, TestResult.failed_count > 0)
        ) or 0
        limit_hits = db.scalar(
            select(func.count()).select_from(AuditLog)
            .where(AuditLog.target_ref == f"task:{t.task_id}", AuditLog.action == "task.retry_limit_exceeded")
        ) or 0
        if failed_runs + failed_tests >= 2 or limit_hits:
            repeated.append(t.task_id)
    if repeated:
        items.append(_item(
            "repeated_failures",
            f"{len(repeated)} task(s) with repeated agent failures or at the retry limit",
            1 + len(repeated), repeated,
        ))

    # Schedule slippage: past the end date with open work, or progress lags the elapsed-time share.
    open_tasks = [t for t in tasks if t.status != TaskStatus.DEPLOYED.value]
    if project.start_date and project.end_date and open_tasks:
        today = now.date()
        span = max(1, (project.end_date - project.start_date).days)
        elapsed = min(1.0, max(0.0, (today - project.start_date).days / span))
        progress = (len(tasks) - len(open_tasks)) / len(tasks)
        if today > project.end_date:
            items.append(_item("schedule_slippage", f"Project end date {project.end_date} has passed with "
                                                    f"{len(open_tasks)} open task(s)", 5, [t.task_id for t in open_tasks]))
        elif elapsed - progress >= SLIPPAGE_GAP:
            items.append(_item(
                "schedule_slippage",
                f"Progress {progress:.0%} is behind the elapsed schedule {elapsed:.0%}",
                1 + round((elapsed - progress) * 5), [t.task_id for t in open_tasks],
            ))

    score = max((i["score"] for i in items), default=0)
    return {"level": level_for(score), "score": score, "items": items}


def latest_report(db: Session, project_id: int) -> RiskReport | None:
    return db.scalars(
        select(RiskReport).where(RiskReport.project_id == project_id).order_by(RiskReport.report_id.desc()).limit(1)
    ).first()


def generate_risk_report(db: Session, project_id: int, now: datetime | None = None) -> RiskReport:
    assessment = assess_risk(db, project_id, now)
    report = RiskReport(
        project_id=project_id, risk_level=assessment["level"], generated_at=now or utcnow(), details=assessment
    )
    db.add(report)
    db.flush()
    return report


def check_risk_threshold(db: Session, project: Project, now: datetime | None = None) -> RiskReport | None:
    """Store a report and alert the PM when the project's risk level newly reaches High (FR-13)."""
    assessment = assess_risk(db, project.project_id, now)
    if assessment["level"] != RiskLevel.HIGH.value:
        return None
    latest = latest_report(db, project.project_id)
    if latest is not None and latest.risk_level == RiskLevel.HIGH.value:
        return None
    report = generate_risk_report(db, project.project_id, now)
    notifications.notify(
        db, kind=NotificationKind.RISK_THRESHOLD, project=project, task=None, to_manager=True,
        message=f"Risk threshold crossed for project '{project.name}': level High (score {assessment['score']}).",
    )
    return report


# -- FR-12 -------------------------------------------------------------------------------------------------------
def dashboard(db: Session, project_id: int | None, now: datetime | None = None) -> dict:
    now = now or utcnow()
    tasks = _tasks(db, project_id)
    by_status = {s.value: 0 for s in TaskStatus}
    by_group = {g.value: 0 for g in StatusGroup}
    for t in tasks:
        by_status[t.status] += 1
        by_group[STATUS_GROUP[TaskStatus(t.status)].value] += 1
    deployed = by_status[TaskStatus.DEPLOYED.value]
    progress = round(100.0 * deployed / len(tasks), 1) if tasks else 0.0

    # Velocity: deployments per 14-day sprint window, last 4 windows, oldest first.
    today = now.date()
    velocity = []
    for i in range(3, -1, -1):
        end = today - timedelta(days=SPRINT_DAYS * i)
        start = end - timedelta(days=SPRINT_DAYS - 1)
        stmt = (
            select(func.count()).select_from(Deployment)
            .join(AgentRun, Deployment.run_id == AgentRun.run_id)
            .join(Task, AgentRun.task_id == Task.task_id)
            .where(
                Deployment.status == "succeeded",
                Deployment.deployed_at >= datetime.combine(start, datetime.min.time()),
                Deployment.deployed_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
            )
        )
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        velocity.append({"sprint_start": start, "sprint_end": end, "deployed": db.scalar(stmt) or 0})

    # Coverage: mean of each task's latest test result (simulated static-check coverage).
    coverages = []
    for t in tasks:
        latest = db.scalars(
            select(TestResult).join(AgentRun, TestResult.run_id == AgentRun.run_id)
            .where(AgentRun.task_id == t.task_id).order_by(TestResult.test_id.desc()).limit(1)
        ).first()
        if latest is not None:
            coverages.append(latest.coverage_pct)
    coverage = {
        "average_pct": round(sum(coverages) / len(coverages), 1) if coverages else None,
        "tasks_with_results": len(coverages),
        "simulated": True,
    }

    if project_id is not None:
        risk = assess_risk(db, project_id, now)
        report = latest_report(db, project_id)
    else:
        projects = list(db.scalars(select(Project.project_id)))
        assessments = [assess_risk(db, pid, now) for pid in projects]
        items = [i for a in assessments for i in a["items"]]
        score = max((a["score"] for a in assessments), default=0)
        risk, report = {"level": level_for(score), "score": score, "items": items}, None

    return {
        "project_id": project_id,
        "totals": {"tasks": len(tasks), "by_status": by_status, "by_group": by_group},
        "progress_pct": progress,
        "velocity": velocity,
        "coverage": coverage,
        "risk": risk,
        "latest_risk_report": report_dict(report) if report else None,
        "generated_at": now,
    }


def report_dict(r: RiskReport) -> dict:
    return {
        "report_id": r.report_id, "project_id": r.project_id, "risk_level": r.risk_level,
        "generated_at": r.generated_at, "details": r.details,
    }

