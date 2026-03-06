"""Runtime harness protocol and PydanticAI implementation (Phase 6)."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

_logger = logging.getLogger(__name__)


class HarnessState(BaseModel):
    """Snapshot of the harness's current state."""

    status: str = "idle"  # idle | running | stopped
    current_phase: str | None = None
    token_usage: int = 0
    step_count: int = 0


class StepResult(BaseModel):
    """Result of a single step execution through the harness."""

    phase: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    token_usage: int = 0


class RuntimeHarness:
    """Protocol-style base class for runtime harness implementations.

    Subclasses must implement ``initialize``, ``execute_step``,
    ``get_state``, and ``cleanup``.
    """

    def initialize(self, run_config: dict[str, Any]) -> None:
        raise NotImplementedError

    def execute_step(self, phase: str, context: dict[str, Any]) -> StepResult:
        raise NotImplementedError

    def get_state(self) -> HarnessState:
        raise NotImplementedError

    def cleanup(self) -> None:
        raise NotImplementedError


class PydanticAIHarness(RuntimeHarness):
    """Default harness wrapping :class:`AgentOrchestrator`.

    When an orchestrator is provided, ``execute_step`` delegates to
    ``AgentOrchestrator.execute()``.  Without one, steps return a
    no-op success result suitable for tests and stub campaigns.
    """

    def __init__(self, *, orchestrator: Any = None) -> None:  # noqa: ANN401
        self._orchestrator = orchestrator
        self._state = HarnessState()

    def initialize(self, run_config: dict[str, Any]) -> None:
        self._state = HarnessState(status="running")
        self._run_config = run_config

    def execute_step(self, phase: str, context: dict[str, Any]) -> StepResult:
        self._state.current_phase = phase

        if self._orchestrator is not None:
            try:
                result = self._execute_with_orchestrator(phase, context)
            except Exception as exc:
                _logger.exception("PydanticAIHarness: orchestrator error in phase %s", phase)
                result = StepResult(phase=phase, success=False, error=str(exc))
        else:
            # No orchestrator — return a no-op success
            result = StepResult(phase=phase, success=True)

        self._state.step_count += 1
        self._state.token_usage += result.token_usage
        return result

    def _execute_with_orchestrator(self, phase: str, context: dict[str, Any]) -> StepResult:
        from openeinstein.agents.orchestrator import DelegatedTask

        prompt = context.get("prompt", "")
        agent_name = context.get("agent", "default")
        task_id = f"{phase}-{self._state.step_count}"

        tasks = [
            DelegatedTask(
                task_id=task_id,
                agent_name=agent_name,
                prompt=prompt,
            )
        ]

        run_id = getattr(self, "_run_config", {}).get("run_id")
        summary = self._orchestrator.execute(tasks, run_id=run_id)

        if summary.results and summary.results[0].success:
            return StepResult(
                phase=phase,
                success=True,
                output=summary.results[0].output,
            )

        error = summary.results[0].error if summary.results else "No results"
        return StepResult(phase=phase, success=False, error=error)

    def get_state(self) -> HarnessState:
        return self._state.model_copy()

    def cleanup(self) -> None:
        self._state.status = "stopped"


class HarnessFactory:
    """Factory for creating harness instances by type name."""

    _registry: dict[str, type[RuntimeHarness]] = {
        "pydantic-ai": PydanticAIHarness,
    }

    @classmethod
    def create(cls, harness_type: str, config: dict[str, Any]) -> RuntimeHarness:
        """Create a harness instance.

        Args:
            harness_type: Registered harness type name (e.g. ``"pydantic-ai"``).
            config: Configuration dict passed to harness constructor.

        Returns:
            A new :class:`RuntimeHarness` instance.

        Raises:
            ValueError: If *harness_type* is not registered.
        """
        klass = cls._registry.get(harness_type)
        if klass is None:
            raise ValueError(
                f"Unknown harness type: {harness_type!r}. "
                f"Available: {sorted(cls._registry)}"
            )
        if harness_type == "pydantic-ai":
            return PydanticAIHarness(orchestrator=config.get("orchestrator"))
        return klass()
