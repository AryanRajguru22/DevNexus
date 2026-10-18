"""Application factory: `uvicorn app.main:create_app --factory` (or `python -m app`). SHARED FILE (owner: Aryan)."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __version__
from .adapters.cicd import CICDAdapter
from .adapters.llm import LLMProvider
from .config import Settings, get_settings
from .errors import install_error_handlers
from .routers import projects, reports, system, tasks
from .services.runtime import build_runtime
from .web.pages import router as pages_router

WEB_DIR = Path(__file__).parent / "web"


def create_app(
    settings: Settings | None = None, llm: LLMProvider | None = None, cicd: CICDAdapter | None = None
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="DevNexus (ASDPIP)",
        version=__version__,
        description="AI-Assisted Software Development & Project Intelligence Platform",
    )
    app.state.runtime = build_runtime(settings, llm=llm, cicd=cicd)
    install_error_handlers(app)
    for module in (system, projects, tasks, reports):
        app.include_router(module.router)
    app.include_router(pages_router)
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    return app

