"""Analytics & Risk Service endpoints: dashboard, estimation, risk (FR-10, FR-11, FR-12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import audit
from ..enums import Role
from ..errors import not_found
from ..models import User
from ..schemas import Dashboard, Estimation, RiskReportOut
from ..security import current_user, get_db, require_roles
from ..services import analytics
from .projects import get_project_or_404

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/dashboard", response_model=Dashboard)
def get_dashboard(project_id: int | None = None, _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if project_id is not None:
        get_project_or_404(db, project_id)
    return analytics.dashboard(db, project_id)


@router.get("/reports/estimation", response_model=Estimation)
def get_estimation(
    request: Request, project_id: int | None = None, _: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    if project_id is not None:
        get_project_or_404(db, project_id)
    return analytics.estimation(db, request.app.state.runtime.git, project_id)


@router.get("/reports/risk", response_model=RiskReportOut)
def get_risk_report(project_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    get_project_or_404(db, project_id)
    report = analytics.latest_report(db, project_id)
    if report is None:
        raise not_found("Risk report (none has been generated for this project yet)")
    return analytics.report_dict(report)


@router.post("/reports/risk", status_code=201, response_model=RiskReportOut)
def create_risk_report(
    project_id: int, user: User = Depends(require_roles(Role.PROJECT_MANAGER)), db: Session = Depends(get_db)
) -> dict:
    get_project_or_404(db, project_id)
    report = analytics.generate_risk_report(db, project_id)
    audit.record(db, user=user, action="risk_report.generate", target_ref=f"risk_report:{report.report_id}",
                 detail=f"project {project_id}: {report.risk_level}")
    db.commit()
    return analytics.report_dict(report)
