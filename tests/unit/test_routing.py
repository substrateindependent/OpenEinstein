"""Unit tests for model routing."""

from __future__ import annotations

from pathlib import Path

from openeinstein.routing import ModelRouter, UsageRecord, load_routing_config


def test_load_routing_config_from_example() -> None:
    cfg = load_routing_config(Path("configs/openeinstein.example.yaml"))
    assert cfg.model_routing.roles.reasoning.default.provider


def test_resolve_role_to_default_model() -> None:
    router = ModelRouter(load_routing_config("configs/openeinstein.example.yaml"))
    resolved = router.resolve("reasoning")
    assert resolved.provider == "anthropic"


def test_resolve_with_fallback_returns_ordered_chain() -> None:
    router = ModelRouter(load_routing_config("configs/openeinstein.example.yaml"))
    chain = router.resolve_with_fallback("generation")
    assert len(chain) >= 2
    assert chain[0].provider == "anthropic"


def test_run_with_fallback_uses_second_config() -> None:
    router = ModelRouter(load_routing_config("configs/openeinstein.example.yaml"))

    def mock_call(cfg: object) -> str:
        provider = getattr(cfg, "provider")
        if provider == "anthropic":
            raise RuntimeError("provider down")
        return provider

    winner = router.run_with_fallback("fast", mock_call)
    assert winner == "openai"


def test_usage_tracking_by_role() -> None:
    router = ModelRouter(load_routing_config("configs/openeinstein.example.yaml"))
    router.record_usage(UsageRecord(role="reasoning", prompt_tokens=10, completion_tokens=20, cost_usd=0.12))
    totals = router.usage_by_role("reasoning")
    assert totals["prompt_tokens"] == 10
    assert totals["completion_tokens"] == 20
    assert totals["cost_usd"] == 0.12
