"""Failure-injection markers for demos and tests (docs/TEAM_CONTRACT.md section 7)."""
from __future__ import annotations

FAIL_LLM = "[fail-llm]"  # first generation attempt fails
FAIL_LLM_ALWAYS = "[fail-llm-always]"
FAIL_TESTS = "[fail-tests]"  # first test run fails
FAIL_TESTS_ALWAYS = "[fail-tests-always]"
FAIL_DEPLOY = "[fail-deploy]"  # first deployment fails


def injected(text: str, once_marker: str, always_marker: str | None, attempt: int) -> bool:
    """True when the mock should fail this attempt (attempts are 1-based)."""
    lowered = text.lower()
    if always_marker and always_marker in lowered:
        return True
    return once_marker in lowered and attempt == 1
