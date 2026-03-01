"""Base agent abstractions with model-role and ToolBus bindings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from openeinstein.gateway.policy import load_policy
from openeinstein.routing import ModelConfig, ModelRole, ModelRouter
from openeinstein.skills import ContextReport, SkillRegistry
from openeinstein.tools import ToolBus, ToolSpec


class AgentBootstrapContext(BaseModel):
    personality: str
    tools_reference: str
    policy_reference: str
    skill_context: str
    context_report: ContextReport


class OpenEinsteinAgent:
    """Base class shared by orchestrator and specialized agents."""

    def __init__(
        self,
        *,
        name: str,
        model_role: ModelRole,
        router: ModelRouter,
        tool_bus: ToolBus,
        skills: SkillRegistry | None = None,
        personality_path: str | Path = Path("src/openeinstein/core/PERSONALITY.md"),
        tools_path: str | Path = Path("src/openeinstein/core/TOOLS.md"),
        policy_path: str | Path = Path("configs/POLICY.json"),
    ) -> None:
        self.name = name
        self.model_role = model_role
        self._router = router
        self._tool_bus = tool_bus
        self._skills = skills
        self._personality_path = Path(personality_path)
        self._tools_path = Path(tools_path)
        self._policy_path = Path(policy_path)

    def resolved_model(self) -> ModelConfig:
        return self._router.resolve(self.model_role)

    def get_tools(self, server_name: str) -> list[ToolSpec]:
        return self._tool_bus.get_tools(server_name)

    def build_bootstrap_context(self, skill_names: list[str] | None = None) -> AgentBootstrapContext:
        personality_text = self._read_file(self._personality_path)
        tools_text = self._read_file(self._tools_path)
        policy = load_policy(self._policy_path)
        policy_reference = (
            f"Policy {policy.version} (enforced_by={policy.enforced_by}); "
            f"approval actions: {', '.join(policy.invariants.require_approval_for)}"
        )
        if self._skills is None:
            bundle_report = ContextReport(max_total_chars=0)
            skill_context = ""
        else:
            bundle = self._skills.build_context(skill_names or [])
            bundle_report = bundle.report
            skill_context = bundle.content

        return AgentBootstrapContext(
            personality=personality_text,
            tools_reference=tools_text,
            policy_reference=policy_reference,
            skill_context=skill_context,
            context_report=bundle_report,
        )

    def build_subagent_context(self, skill_names: list[str] | None = None) -> AgentBootstrapContext:
        context = self.build_bootstrap_context(skill_names)
        # Sub-agents get policy/persona and skill context, but omit verbose tool docs.
        return context.model_copy(update={"tools_reference": ""})

    def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("Subclasses must implement run()")

    @staticmethod
    def _read_file(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
