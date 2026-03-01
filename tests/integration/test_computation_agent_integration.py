"""Integration test for computation agent runtime flow."""

from __future__ import annotations

import json
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


def _gate(payload: dict[str, object]) -> GateResult:
    return GateResult(name="bounded", passed=bool(payload.get("bounded")), reason="bounded")


def test_computation_agent_gate_failure_path(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server(
        "sympy",
        InMemoryToolServer(
            {"evaluate": lambda args: {"expr": args["expression"], "bounded": False}}
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
        gate_sequence=[_gate],
    )
    result = agent.run(
        "compute",
        template="u({{x}})",
        variables={"x": 5},
        run_id="run-compute-int",
    )
    assert result["success"] is False
    assert "Gate failed" in result["error"]
