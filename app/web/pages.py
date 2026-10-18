"""HTML page routes. Pages are shells: data is loaded by static/js/app.js from the REST API (no fake data)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _page(request: Request, template: str, nav: str, title: str, **ctx: object) -> HTMLResponse:
    return templates.TemplateResponse(request, template, {"nav": nav, "title": title, **ctx})


@router.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    return _page(request, "dashboard.html", "dashboard", "Dashboard")


@router.get("/projects", response_class=HTMLResponse)
def projects_page(request: Request) -> HTMLResponse:
    return _page(request, "projects.html", "projects", "Projects")


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_page(request: Request, project_id: int) -> HTMLResponse:
    return _page(request, "project.html", "projects", "Project", project_id=project_id)


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_page(request: Request, task_id: int) -> HTMLResponse:
    return _page(request, "task.html", "projects", "Task", task_id=task_id)


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request) -> HTMLResponse:
    return _page(request, "reports.html", "reports", "Reports")


@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request) -> HTMLResponse:
    return _page(request, "audit.html", "audit", "Audit trail")


@router.get("/notifications", response_class=HTMLResponse)
def notifications_page(request: Request) -> HTMLResponse:
    return _page(request, "notifications.html", "notifications", "Notifications")
