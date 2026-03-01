"""Integration tests for template registry usage in computation runtime path."""

from __future__ import annotations

import json
from pathlib import Path

from openeinstein.agents import ComputationAgent, GateResult
from openeinstein.campaigns import BackendTemplate, ComputeTemplate, TemplateRegistry
from openeinstein.routing import ModelRouter, RoutingConfig
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


def _router() -> ModelRouter:
    return ModelRouter(
        RoutingConfig.model_validate(
            {
                "model_routing": {
                    "roles": {
                        "reasoning": {
                            "description": "reasoning",
                            "default": {"provider": "p", "model": "m-r"},
                        },
                        "generation": {
                            "description": "generation",
                            "default": {"provider": "p", "model": "m-g"},
                        },
                        "fast": {
                            "description": "fast",
                            "default": {"provider": "p", "model": "m-f"},
                        },
                        "embeddings": {
                            "description": "embeddings",
                            "default": {"provider": "p", "model": "m-e"},
                        },
                    }
                }
            }
        )
    )


def _policy(path: Path) -> Path:
    target = path / "policy.json"
    target.write_text(
        json.dumps(
            {
                "version": "1.0",
                "invariants": {
                    "require_approval_for": [],
                    "max_llm_calls_per_step": 50,
                    "max_cas_timeout_minutes": 60,
                    "forbidden_operations": [],
                    "require_verification_after_gates": True,
                },
                "enforced_by": "gateway",
                "note": "test",
            }
        ),
        encoding="utf-8",
    )
    return target


def _gate(payload: dict[str, object]) -> GateResult:
    return GateResult(name="ok", passed=bool(payload.get("ok")), reason="check")


def test_template_registry_used_by_computation_agent(tmp_path: Path) -> None:
    registry = TemplateRegistry()
    registry.register(
        ComputeTemplate(
            template_id="expr",
            version="1.0.0",
            backends=[
                BackendTemplate(backend="primary", body="P({{x}})"),
                BackendTemplate(backend="fallback", body="F({{x}})"),
            ],
        )
    )

    manager = MCPConnectionManager()
    manager.register_server(
        "primary",
        InMemoryToolServer({"evaluate": lambda args: (_ for _ in ()).throw(RuntimeError("primary failed"))}),
    )
    manager.register_server("fallback", InMemoryToolServer({"evaluate": lambda args: {"ok": True, "expr": args["expression"]}}))
    bus = ToolBus(manager)

    agent = ComputationAgent(
        name="compute",
        model_role="reasoning",
        router=_router(),
        tool_bus=bus,
        policy_path=_policy(tmp_path),
        cas_server="primary",
        cas_tool="evaluate",
        gate_sequence=[_gate],
        template_registry=registry,
    )

    result = agent.run(
        "compute",
        template_id="expr",
        variables={"x": 7},
        fallback_server="fallback",
        run_id="run-template",
    )
    assert result["success"] is True
    assert result["selected_server"] == "fallback"
    assert result["tool_result"]["expr"] == "F(7)"
