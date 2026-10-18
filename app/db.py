"""Engine/session factory, schema creation and seed data. SHARED FILE (owner: Aryan)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .enums import AgentType, Role
from .models import Agent, Base, User

DEMO_USERS = [
    ("Aryan (Project Manager)", "aryan@devnexus.example", Role.PROJECT_MANAGER),
    ("Member C (Developer)", "member-c@devnexus.example", Role.DEVELOPER),
    ("Member B (Developer)", "member-b@devnexus.example", Role.DEVELOPER),
]


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=True)


def init_db(engine: Engine, session_factory: sessionmaker[Session], seed_demo_users: bool = True) -> None:
    """Create tables and seed the three agents (always) and the demo users (if the table is empty)."""
    Base.metadata.create_all(engine)
    with session_factory() as db:
        existing = {a.type for a in db.scalars(select(Agent))}
        for agent_type in AgentType:
            if agent_type.value not in existing:
                db.add(Agent(type=agent_type.value, status="available"))
        if seed_demo_users and db.scalar(select(User.user_id).limit(1)) is None:
            for name, email, role in DEMO_USERS:
                db.add(User(name=name, email=email, role=role.value))
        db.commit()
