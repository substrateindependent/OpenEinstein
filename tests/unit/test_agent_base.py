"""Unit tests for base agent abstractions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openeinstein.agents import OpenEinsteinAgent
from openeinstein.routing import ModelRouter, RoutingConfig
from openeinstein.skills import SkillRegistry
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


class DummyAgent(OpenEinsteinAgent):
    def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"ok": True}


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


def test_agent_base_bindings_and_bootstrap_context(tmp_path: Path) -> None:
    personality = tmp_path / "PERSONALITY.md"
    tools_md = tmp_path / "TOOLS.md"
    policy = tmp_path / "POLICY.json"
    personality.write_text("Persona text", encoding="utf-8")
    tools_md.write_text("Tools text", encoding="utf-8")
    policy.write_text(
        json.dumps(
            {
                "version": "1.0",
                "invariants": {
                    "require_approval_for": ["shell_exec"],
                    "max_llm_calls_per_step": 50,
                    "max_cas_timeout_minutes": 60,
                    "forbidden_operations": [],
                    "require_verification_after_gates": True,
                },
                "enforced_by": "gateway",
                "note": "policy",
            }
        ),
        encoding="utf-8",
    )

    skills_root = tmp_path / "skills" / "alpha"
    skills_root.mkdir(parents=True, exist_ok=True)
    (skills_root / "SKILL.md").write_text("# Alpha\nUse alpha flow", encoding="utf-8")
    skill_registry = SkillRegistry([tmp_path / "skills"])

    manager = MCPConnectionManager()
    manager.register_server("local", InMemoryToolServer({"echo": lambda args: args}))
    bus = ToolBus(manager)

    agent = DummyAgent(
        name="dummy",
        model_role="reasoning",
        router=_router(),
        tool_bus=bus,
        skills=skill_registry,
        personality_path=personality,
        tools_path=tools_md,
        policy_path=policy,
    )

    assert agent.resolved_model().model == "m-r"
    assert agent.get_tools("local")[0].name == "echo"
    context = agent.build_bootstrap_context(["alpha"])
    assert "Persona text" in context.personality
    assert "Tools text" in context.tools_reference
    assert "shell_exec" in context.policy_reference
    assert "Skill: alpha" in context.skill_context
    sub_context = agent.build_subagent_context(["alpha"])
    assert sub_context.tools_reference == ""
