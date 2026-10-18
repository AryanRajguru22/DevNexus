"""Runtime settings, read from environment variables (see README for the list)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_url: str
    # Artificial pause (seconds) inside the mock agents so the "Generating"/"Testing" states are
    # visible during a live demo. 0 in tests.
    mock_agent_delay: float = 0.0
    seed_demo_users: bool = True


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("DEVNEXUS_DATA_DIR", "data")).resolve()
    default_url = f"sqlite:///{(data_dir / 'devnexus.db').as_posix()}"
    return Settings(
        data_dir=data_dir,
        database_url=os.environ.get("DEVNEXUS_DATABASE_URL", default_url),
        mock_agent_delay=float(os.environ.get("DEVNEXUS_MOCK_AGENT_DELAY", "0")),
        seed_demo_users=os.environ.get("DEVNEXUS_SEED_DEMO_USERS", "1") != "0",
    )
