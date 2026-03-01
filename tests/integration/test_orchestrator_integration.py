"""Integration tests for orchestrator with bound subagents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openeinstein.agents import AgentOrchestrator, DelegatedTask, OpenEinsteinAgent
from openeinstein.routing import ModelRouter, RoutingConfig
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


class ToolAwareAgent(OpenEinsteinAgent):
    def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
        tools = self.get_tools("local")
        return {"prompt": prompt, "tool_count": len(tools)}


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


def test_orchestrator_runtime_flow(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("local", InMemoryToolServer({"echo": lambda args: args}))
    bus = ToolBus(manager)
    policy_path = _policy(tmp_path)
    agent = ToolAwareAgent(
        name="subagent",
        model_role="reasoning",
        router=_router(),
        tool_bus=bus,
        policy_path=policy_path,
    )
    orchestrator = AgentOrchestrator({"subagent": agent})
    summary = orchestrator.execute(
        [
            DelegatedTask(task_id="known", agent_name="subagent", prompt="do work"),
            DelegatedTask(task_id="unknown", agent_name="missing", prompt="fail"),
        ],
        run_id="run-int",
    )
    assert summary.aggregated_output["known"]["tool_count"] == 1
    failed = [item for item in summary.results if item.task_id == "unknown"][0]
    assert failed.success is False
