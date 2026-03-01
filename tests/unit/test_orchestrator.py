"""Unit tests for orchestrator behavior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openeinstein.agents import AgentOrchestrator, DelegatedTask, OpenEinsteinAgent
from openeinstein.routing import ModelRouter, RoutingConfig
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


class MockAgent(OpenEinsteinAgent):
    def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"agent": self.name, "prompt": prompt}


def _router() -> ModelRouter:
    config = RoutingConfig.model_validate(
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
    return ModelRouter(config)


def _policy_file(path: Path) -> Path:
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


def test_orchestrator_delegation_aggregation_and_adaptive_order(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("local", InMemoryToolServer({"echo": lambda args: args}))
    bus = ToolBus(manager)
    policy_path = _policy_file(tmp_path)

    agents: dict[str, OpenEinsteinAgent] = {
        "a": MockAgent(
            name="a",
            model_role="reasoning",
            router=_router(),
            tool_bus=bus,
            policy_path=policy_path,
        ),
        "b": MockAgent(
            name="b",
            model_role="generation",
            router=_router(),
            tool_bus=bus,
            policy_path=policy_path,
        ),
    }
    orchestrator = AgentOrchestrator(agents, invariants=["POLICY_ENFORCED"], max_compacted_chars=80)

    tasks = [
        DelegatedTask(task_id="t1", agent_name="a", prompt="A" * 200, priority=1),
        DelegatedTask(task_id="t2", agent_name="b", prompt="B" * 30, priority=0),
    ]
    summary = orchestrator.execute(tasks, failure_scores={"t1": 2, "t2": 0}, run_id="run-o")
    assert summary.execution_order == ["t2", "t1"]
    assert summary.aggregated_output["t2"]["agent"] == "b"
    assert "POLICY_ENFORCED" in summary.aggregated_output["t1"]["prompt"]


def test_compaction_reinjects_invariants_within_budget() -> None:
    orchestrator = AgentOrchestrator(
        {},
        invariants=["POLICY_ENFORCED", "PERSONA_GUARD"],
        max_compacted_chars=120,
    )
    compacted = orchestrator.compact_with_invariants("x" * 500, ["POLICY_ENFORCED", "PERSONA_GUARD"])
    assert "POLICY_ENFORCED" in compacted
    assert "PERSONA_GUARD" in compacted
    assert len(compacted) <= 120
