"""Integration tests for verification agent output flow."""

from __future__ import annotations

import json
from pathlib import Path

from openeinstein.agents import VerificationAgent
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


def test_verification_agent_no_inconsistency_path(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("local", InMemoryToolServer({"noop": lambda args: args}))
    bus = ToolBus(manager)
    agent = VerificationAgent(
        name="verify",
        model_role="reasoning",
        router=_router(),
        tool_bus=bus,
        policy_path=_policy(tmp_path),
    )
    report = agent.run(
        "verify",
        claims=[
            {"key": "ghost_free", "value": True, "source": "calc-a"},
            {"key": "stable", "value": True, "source": "calc-b"},
        ],
    )
    assert report["inconsistent"] is False
    assert report["review_required"] is False
    assert report["summary"] == "No inconsistencies detected."
