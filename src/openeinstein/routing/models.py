"""Typed models for role-based model routing."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ModelRole = Literal["reasoning", "generation", "fast", "embeddings"]


class ModelConfig(BaseModel):
    """Provider/model selection and optional parameters."""

    provider: str
    model: str
    params: dict[str, Any] = Field(default_factory=dict)


class RoleConfig(BaseModel):
    """Configuration for a logical model role."""

    description: str
    default: ModelConfig
    fallback: ModelConfig | list[ModelConfig] | None = None

    def fallback_chain(self) -> list[ModelConfig]:
        if self.fallback is None:
            return []
        if isinstance(self.fallback, list):
            return self.fallback
        return [self.fallback]


class RoutingRoles(BaseModel):
    """Role map under model_routing.roles."""

    reasoning: RoleConfig
    generation: RoleConfig
    fast: RoleConfig
    embeddings: RoleConfig


class RoutingRoot(BaseModel):
    """Top-level model routing root."""

    roles: RoutingRoles


class RoutingConfig(BaseModel):
    """Validated routing configuration."""

    model_routing: RoutingRoot


class UsageRecord(BaseModel):
    """Single token/cost usage event."""

    role: ModelRole
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
