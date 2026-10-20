"""Wiring of the application: engine, sessions, adapters and the three agents."""
from __future__ import annotations

import threading
from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..adapters.cicd import CICDAdapter, MockCICDAdapter
from ..adapters.git_local import LocalGitAdapter
from ..adapters.llm import LLMProvider, create_provider
from ..agents.codegen import CodeGenerationAgent
from ..agents.deployment import DeploymentAgent
from ..agents.testing import TestingAgent
from ..config import Settings
from ..db import init_db, make_engine, make_session_factory


@dataclass
class Runtime:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    git: LocalGitAdapter
    llm: LLMProvider
    cicd: CICDAdapter
    codegen: CodeGenerationAgent
    testing: TestingAgent
    deployment: DeploymentAgent
    recovery_thread: threading.Thread | None = None  # set when startup recovery re-dispatched interrupted jobs


def build_runtime(settings: Settings, llm: LLMProvider | None = None, cicd: CICDAdapter | None = None) -> Runtime:
    llm = llm or create_provider(settings.llm_provider)  # unknown provider name: fail before touching the database
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    init_db(engine, session_factory, seed_demo_users=settings.seed_demo_users)
    git = LocalGitAdapter(settings.data_dir / "workspace")
    cicd = cicd or MockCICDAdapter()
    runtime = Runtime(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        git=git,
        llm=llm,
        cicd=cicd,
        codegen=CodeGenerationAgent(llm, git),
        testing=TestingAgent(git),
        deployment=DeploymentAgent(git, cicd),
    )
    if settings.recover_on_startup:
        start_recovery(runtime)
    return runtime


def start_recovery(runtime: Runtime) -> None:
    """Repair agent jobs interrupted by the previous shutdown, then re-run them in the background (NFR-5).

    The database repair is synchronous (so the state is consistent before the first request is served); the
    re-dispatched agent jobs run on one daemon thread so application start-up is never blocked by an agent.
    Assumes a single application process per database: at start-up no other process is running a job.
    """
    from . import orchestrator  # imported here: orchestrator imports Runtime from this module

    jobs = orchestrator.recover_interrupted(runtime)
    if jobs:
        runtime.recovery_thread = threading.Thread(
            target=orchestrator.run_recovered_jobs, args=(runtime, jobs), name="devnexus-recovery", daemon=True
        )
        runtime.recovery_thread.start()
