"""Integration test for routing fallback behavior with mock LLM call path."""

from __future__ import annotations

from openeinstein.routing import ModelRouter, load_routing_config


def test_routing_fallback_integration() -> None:
    router = ModelRouter(load_routing_config("configs/openeinstein.example.yaml"))

    def mock_llm_call(model_cfg: object) -> str:
        provider = getattr(model_cfg, "provider")
        if provider == "anthropic":
            raise RuntimeError("mock transient failure")
        return f"ok:{provider}"

    assert router.run_with_fallback("generation", mock_llm_call).startswith("ok:")
