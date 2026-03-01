"""Model routing implementation and configuration loading."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable, TypeVar

import yaml  # type: ignore[import-untyped]

from openeinstein.routing.models import (
    ModelConfig,
    ModelRole,
    RoleConfig,
    RoutingConfig,
    UsageRecord,
)

T = TypeVar("T")


class ModelRouter:
    """Resolve logical roles and execute callables with fallback behavior."""

    def __init__(self, config: RoutingConfig) -> None:
        self._config = config
        self._usage_records: list[UsageRecord] = []
        self._usage_totals: dict[ModelRole, dict[str, float]] = defaultdict(
            lambda: {"prompt_tokens": 0.0, "completion_tokens": 0.0, "cost_usd": 0.0}
        )

    @property
    def config(self) -> RoutingConfig:
        return self._config

    def _role_config(self, role: ModelRole) -> RoleConfig:
        return getattr(self._config.model_routing.roles, role)

    def resolve(self, role: ModelRole) -> ModelConfig:
        """Resolve a role to its default model configuration."""

        return self._role_config(role).default

    def resolve_with_fallback(self, role: ModelRole) -> list[ModelConfig]:
        """Resolve role to ordered primary + fallback chain."""

        role_config = self._role_config(role)
        return [role_config.default, *role_config.fallback_chain()]

    def run_with_fallback(self, role: ModelRole, call: Callable[[ModelConfig], T]) -> T:
        """Run a callback with role config and fall back on failure."""

        errors: list[str] = []
        for config in self.resolve_with_fallback(role):
            try:
                return call(config)
            except Exception as exc:  # pragma: no cover - tested by behavior
                errors.append(f"{config.provider}/{config.model}: {exc}")
        raise RuntimeError(f"All providers failed for role '{role}': {' | '.join(errors)}")

    def record_usage(self, usage: UsageRecord) -> None:
        """Record token and cost usage for a role."""

        self._usage_records.append(usage)
        totals = self._usage_totals[usage.role]
        totals["prompt_tokens"] += usage.prompt_tokens
        totals["completion_tokens"] += usage.completion_tokens
        totals["cost_usd"] += usage.cost_usd

    def usage_by_role(self, role: ModelRole) -> dict[str, float]:
        """Return accumulated token/cost metrics for a role."""

        return dict(self._usage_totals[role])

    @property
    def usage_records(self) -> list[UsageRecord]:
        return list(self._usage_records)


def load_routing_config(path: str | Path) -> RoutingConfig:
    """Load routing config from YAML and validate with Pydantic."""

    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return RoutingConfig.model_validate(payload)
