"""Code Generation Agent (FR-5): asks the LLM provider for code and commits it to a feature branch only."""
from __future__ import annotations

from dataclasses import dataclass

from ..adapters.git_local import LocalGitAdapter, ProtectedBranchError
from ..adapters.llm import CodeRequest, LLMProvider, LLMUnavailable
from ..enums import AgentType
from .base import AgentError


@dataclass(frozen=True)
class CodegenResult:
    files: list[str]
    loc: int
    summary: str


class CodeGenerationAgent:
    agent_type = AgentType.CODE_GENERATION

    def __init__(self, llm: LLMProvider, git: LocalGitAdapter):
        self.llm = llm
        self.git = git

    def run(
        self,
        *,
        project_id: int,
        branch: str,
        title: str,
        description: str,
        requirement: str,
        feedback: str | None,
        attempt: int,
        max_loc: int,
    ) -> CodegenResult:
        request = CodeRequest(title, description, requirement, feedback, attempt, max_loc)
        try:
            generated = self.llm.generate(request)
        except LLMUnavailable as exc:
            raise AgentError(str(exc)) from exc
        loc = sum(1 for text in generated.files.values() for line in text.splitlines() if line.strip())
        if loc > max_loc:
            raise AgentError(f"Generated code has {loc} lines, above the pipeline limit of {max_loc}")
        try:
            self.git.commit(project_id, branch, generated.files, f"Generate code for: {title}")
        except ProtectedBranchError as exc:
            raise AgentError(str(exc)) from exc
        return CodegenResult(files=sorted(generated.files), loc=loc, summary=generated.summary)
