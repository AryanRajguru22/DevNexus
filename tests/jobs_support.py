"""Helpers shared by tests/test_recovery.py and tests/test_orchestrator_guard.py (not a test module).

Crashes are simulated honestly: `Crash` derives from BaseException, so the orchestrator's `except Exception`
does not catch it and the run is left `running` with the task in Generating - exactly what a killed process leaves.
"""
from __future__ import annotations

import threading
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import workflow
from app.adapters.llm import CodeRequest, GeneratedCode, MockLLMProvider
from app.main import create_app
from app.models import AgentRun, AuditLog, Deployment, Notification, Task, TestResult, User
from app.services.tasks import fire
from tests.conftest import DEV1_ID, Api


class Crash(BaseException):
    """Stands in for the process being killed mid-job."""


class CrashingLLM:
    name = "crashing-test-llm"

    def generate(self, request: CodeRequest) -> GeneratedCode:
        raise Crash()


class BlockingLLM:
    """Holds the first generation open until the test releases it, so two jobs really overlap."""

    name = "blocking-test-llm"

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self._mock = MockLLMProvider()

    def generate(self, request: CodeRequest) -> GeneratedCode:
        self.calls += 1
        self.entered.set()
        assert self.release.wait(20), "test never released the blocked generation"
        return self._mock.generate(request)


@pytest.fixture
def boot(settings):
    """boot(recover=False, llm=None) -> app on the shared temp database; every app is joined and disposed."""
    apps = []

    def _boot(*, recover: bool = False, llm=None):
        app = create_app(replace(settings, recover_on_startup=recover), llm=llm)
        apps.append(app)
        return app

    yield _boot
    for app in apps:
        thread = app.state.runtime.recovery_thread
        if thread is not None:
            thread.join(20)
        app.state.runtime.engine.dispose()


def new_task(app, title: str = "Build login API", retry_limit: int = 2) -> int:
    """A Created task in a fresh project, built through the real API."""
    api = Api(TestClient(app))
    project = api.project()
    api.pipeline(project["project_id"], retry_limit=retry_limit)
    req = api.requirement(project["project_id"])
    return api.task(project["project_id"], req["req_id"], title)["task_id"]


def fire_as_developer(rt, task_id: int, event: str, detail: str | None = None) -> None:
    """Apply a human transition WITHOUT dispatching its background job (the job is what a crash loses)."""
    with rt.session_factory() as db:
        fire(db, db.get(Task, task_id), event, workflow.Actor(user=db.get(User, DEV1_ID)), detail=detail)
        db.commit()


def snapshot(rt, task_id: int) -> dict:
    with rt.session_factory() as db:
        task = db.get(Task, task_id)
        runs = list(db.scalars(select(AgentRun).where(AgentRun.task_id == task_id).order_by(AgentRun.run_id)))
        run_ids = [r.run_id for r in runs]
        count = lambda model, *where: db.scalar(select(func.count()).select_from(model).where(*where)) or 0  # noqa: E731
        return {
            "status": task.status,
            "runs": [(r.status, r.error_message) for r in runs],
            "tests": count(TestResult, TestResult.run_id.in_(run_ids)) if run_ids else 0,
            "deployments": count(Deployment, Deployment.run_id.in_(run_ids)) if run_ids else 0,
            "audit": [a.action for a in db.scalars(select(AuditLog).where(AuditLog.target_ref == f"task:{task_id}").order_by(AuditLog.log_id))],
            "audit_total": count(AuditLog),
            "notifications": count(Notification),
        }
