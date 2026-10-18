"""Wiring of the application: engine, sessions, adapters and the three agents."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..adapters.cicd import CICDAdapter, MockCICDAdapter
from ..adapters.git_local import LocalGitAdapter
from ..adapters.llm import LLMProvider, MockLLMProvider
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


def build_runtime(settings: Settings, llm: LLMProvider | None = None, cicd: CICDAdapter | None = None) -> Runtime:
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    init_db(engine, session_factory, seed_demo_users=settings.seed_demo_users)
    git = LocalGitAdapter(settings.data_dir / "workspace")
    llm = llm or MockLLMProvider()
    cicd = cicd or MockCICDAdapter()
    return Runtime(
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
