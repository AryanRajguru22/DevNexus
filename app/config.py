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
    # Name of the LLM provider (see adapters/llm.PROVIDERS). "mock" is the only built-in one.
    llm_provider: str = "mock"
    # Re-dispatch agent jobs interrupted by a restart when the application starts (NFR-5, services/orchestrator).
    recover_on_startup: bool = True


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("DEVNEXUS_DATA_DIR", "data")).resolve()
    default_url = f"sqlite:///{(data_dir / 'devnexus.db').as_posix()}"
    return Settings(
        data_dir=data_dir,
        database_url=os.environ.get("DEVNEXUS_DATABASE_URL", default_url),
        mock_agent_delay=float(os.environ.get("DEVNEXUS_MOCK_AGENT_DELAY", "0")),
        seed_demo_users=os.environ.get("DEVNEXUS_SEED_DEMO_USERS", "1") != "0",
        llm_provider=os.environ.get("DEVNEXUS_LLM_PROVIDER", "mock").strip().lower(),
        recover_on_startup=os.environ.get("DEVNEXUS_RECOVER_ON_STARTUP", "1") != "0",
    )
