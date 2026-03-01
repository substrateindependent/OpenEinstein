"""Unit tests for computation agent gate sequence and fallback behavior."""

from __future__ import annotations

import json
import time
from pathlib import Path

from openeinstein.agents import ComputationAgent, GateResult
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


def _stable_gate(payload: dict[str, object]) -> GateResult:
    return GateResult(name="stable", passed=bool(payload.get("stable")), reason="stable check")


def _bounded_gate(payload: dict[str, object]) -> GateResult:
    return GateResult(name="bounded", passed=bool(payload.get("bounded")), reason="bounded check")


def test_computation_agent_full_gate_sequence(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server(
        "sympy",
        InMemoryToolServer(
            {
                "evaluate": lambda args: {
                    "value": args["expression"],
                    "stable": True,
                    "bounded": True,
                }
            }
        ),
    )
    bus = ToolBus(manager)
    agent = ComputationAgent(
        name="compute",
        model_role="reasoning",
        router=_router(),
        tool_bus=bus,
        policy_path=_policy(tmp_path),
        cas_server="sympy",
        cas_tool="evaluate",
        gate_sequence=[_stable_gate, _bounded_gate],
    )
    result = agent.run(
        "compute",
        template="f({{x}}) + {{y}}",
        variables={"x": 1, "y": 2},
        run_id="run-compute",
    )
    assert result["success"] is True
    assert result["rendered_expression"] == "f(1) + 2"
    assert len(result["gates"]) == 2


def test_computation_agent_timeout_and_fallback(tmp_path: Path) -> None:
    manager = MCPConnectionManager()

    def slow_eval(args: dict[str, object]) -> dict[str, object]:  # noqa: ARG001
        time.sleep(0.2)
        return {"value": "slow", "stable": True, "bounded": True}

    manager.register_server("primary", InMemoryToolServer({"evaluate": slow_eval}))
    manager.register_server(
        "fallback",
        InMemoryToolServer(
            {
                "evaluate": lambda args: {
                    "value": args["expression"],
                    "stable": True,
                    "bounded": True,
                }
            }
        ),
    )
    bus = ToolBus(manager)
    agent = ComputationAgent(
        name="compute",
        model_role="reasoning",
        router=_router(),
        tool_bus=bus,
        policy_path=_policy(tmp_path),
        cas_server="primary",
        cas_tool="evaluate",
        gate_sequence=[_stable_gate, _bounded_gate],
    )
    result = agent.run(
        "compute",
        template="{{expr}}",
        variables={"expr": "x**2"},
        timeout_seconds=0.05,
        fallback_server="fallback",
        run_id="run-fallback",
    )
    assert result["success"] is True
    assert result["selected_server"] == "fallback"
