"""CI/CD runner interface and mock. LABEL: nothing is really built or deployed (deviation D-4)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .markers import FAIL_DEPLOY, injected


@dataclass(frozen=True)
class CICDResult:
    succeeded: bool
    message: str


class CICDAdapter(Protocol):
    def deploy(self, *, branch: str, environment: str, attempt: int, hints: str) -> CICDResult: ...


class MockCICDAdapter:
    def deploy(self, *, branch: str, environment: str, attempt: int, hints: str) -> CICDResult:
        if injected(hints, FAIL_DEPLOY, None, attempt):
            return CICDResult(False, f"Simulated CI/CD failure while deploying {branch} to {environment}")
        return CICDResult(True, f"Simulated deployment of {branch} to {environment} succeeded")
