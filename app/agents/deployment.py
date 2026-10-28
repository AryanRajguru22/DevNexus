"""Deployment Agent (FR-9): merges the approved branch and triggers the CI/CD runner; rolls back on failure.

It is only ever called after an explicit human authorisation has been recorded (UC-07).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..adapters.cicd import CICDAdapter
from ..adapters.git_local import LocalGitAdapter
from ..enums import AgentType


@dataclass(frozen=True)
class DeployResult:
    succeeded: bool
    message: str


class DeploymentAgent:
    agent_type = AgentType.DEPLOYMENT

    def __init__(self, git: LocalGitAdapter, cicd: CICDAdapter):
        self.git = git
        self.cicd = cicd

    def deploy(self, *, project_id: int, branch: str, environment: str, hints: str, attempt: int) -> DeployResult:
        snapshot = self.git.merge_to_main(project_id, branch)
        try:
            result = self.cicd.deploy(branch=branch, environment=environment, attempt=attempt, hints=hints)
        except Exception:
            # A runner that raises (network error, timeout, bug) must leave main exactly as it was too (issue #16);
            # the orchestrator records the failure. Scope: this restores the mock workspace directory only - there
            # is no real external deployment to undo.
            self.git.rollback(project_id, snapshot)
            raise
        if not result.succeeded:
            self.git.rollback(project_id, snapshot)  # main is restored: a failed deployment leaves no trace
            return DeployResult(False, f"{result.message}; merge rolled back")
        return DeployResult(True, result.message)
