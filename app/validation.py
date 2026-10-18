"""Validation rules: pipeline configuration (FR-3, A-2) and requirement checks (class Requirement.validate()).

Owner: Member B. The shapes follow docs/TEAM_CONTRACT.md section 3.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .enums import AgentType, Environment


class Constraints(BaseModel):
    max_loc: int = Field(200, ge=30, le=2000, description="Maximum lines of generated code per run (NFR-1 scope)")
    target_environment: Environment = Environment.STAGING
    delay_threshold_hours: int = Field(72, ge=1, le=720, description="A task idle longer than this is 'delayed'")


class PipelineConfig(BaseModel):
    active_agents: list[AgentType] = Field(default_factory=lambda: list(AgentType))
    retry_limit: int = Field(2, ge=0, le=10)
    constraints: Constraints = Field(default_factory=Constraints)

    @field_validator("active_agents")
    @classmethod
    def _unique(cls, v: list[AgentType]) -> list[AgentType]:
        if len(set(v)) != len(v):
            raise ValueError("active_agents must not contain duplicates")
        return v

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def is_active(self, agent_type: AgentType | str) -> bool:
        return AgentType(agent_type) in self.active_agents


def default_pipeline() -> dict[str, Any]:
    return PipelineConfig().to_json()


def load_pipeline(raw: dict[str, Any] | None) -> PipelineConfig:
    """Parse a stored pipeline_config, falling back to defaults for missing keys."""
    return PipelineConfig.model_validate(raw or {})
