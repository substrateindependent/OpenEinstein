"""Unit tests for runtime harness protocol and PydanticAI implementation (Story 6.1)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from openeinstein.agents.harness import (
    HarnessFactory,
    HarnessState,
    PydanticAIHarness,
    RuntimeHarness,
    StepResult,
)


class TestRuntimeHarnessProtocol:
    def test_pydantic_ai_harness_satisfies_protocol(self) -> None:
        """PydanticAIHarness is structurally compatible with RuntimeHarness."""
        harness = PydanticAIHarness()
        assert isinstance(harness, RuntimeHarness)

    def test_harness_state_defaults(self) -> None:
        state = HarnessState()
        assert state.status == "idle"
        assert state.current_phase is None
        assert state.token_usage == 0
        assert state.step_count == 0

    def test_step_result_defaults(self) -> None:
        result = StepResult(phase="generating", success=True)
        assert result.phase == "generating"
        assert result.success is True
        assert result.output == {}
        assert result.error is None
        assert result.token_usage == 0


class TestPydanticAIHarness:
    def test_initialize_sets_running_state(self) -> None:
        harness = PydanticAIHarness()
        harness.initialize({"run_id": "test-001"})
        state = harness.get_state()
        assert state.status == "running"

    def test_execute_step_delegates_to_orchestrator(self) -> None:
        """execute_step delegates to AgentOrchestrator.execute when orchestrator is set."""
        from openeinstein.agents.orchestrator import (
            OrchestrationSummary,
            TaskResult,
        )

        mock_orch = MagicMock()
        mock_orch.execute.return_value = OrchestrationSummary(
            execution_order=["task-1"],
            results=[
                TaskResult(
                    task_id="task-1",
                    agent_name="computation",
                    success=True,
                    output={"key": "value"},
                )
            ],
            aggregated_output={"task-1": {"key": "value"}},
        )

        harness = PydanticAIHarness(orchestrator=mock_orch)
        harness.initialize({"run_id": "test-001"})
        result = harness.execute_step(
            "generating",
            {"prompt": "test prompt", "agent": "computation"},
        )

        assert result.success is True
        assert result.phase == "generating"
        mock_orch.execute.assert_called_once()

    def test_execute_step_without_orchestrator_returns_noop(self) -> None:
        """execute_step without orchestrator returns a no-op success result."""
        harness = PydanticAIHarness()
        harness.initialize({})
        result = harness.execute_step("planning", {})
        assert result.success is True
        assert result.phase == "planning"

    def test_execute_step_increments_step_count(self) -> None:
        harness = PydanticAIHarness()
        harness.initialize({})
        harness.execute_step("planning", {})
        harness.execute_step("generating", {})
        state = harness.get_state()
        assert state.step_count == 2

    def test_execute_step_tracks_current_phase(self) -> None:
        harness = PydanticAIHarness()
        harness.initialize({})
        harness.execute_step("gating", {})
        state = harness.get_state()
        assert state.current_phase == "gating"

    def test_execute_step_handles_orchestrator_error(self) -> None:
        mock_orch = MagicMock()
        mock_orch.execute.side_effect = RuntimeError("orchestrator crashed")

        harness = PydanticAIHarness(orchestrator=mock_orch)
        harness.initialize({})
        result = harness.execute_step("generating", {})
        assert result.success is False
        assert "orchestrator crashed" in (result.error or "")

    def test_cleanup_sets_stopped_state(self) -> None:
        harness = PydanticAIHarness()
        harness.initialize({})
        harness.cleanup()
        state = harness.get_state()
        assert state.status == "stopped"

    def test_cleanup_is_idempotent(self) -> None:
        harness = PydanticAIHarness()
        harness.initialize({})
        harness.cleanup()
        harness.cleanup()  # should not raise
        state = harness.get_state()
        assert state.status == "stopped"

    def test_get_state_before_initialize(self) -> None:
        harness = PydanticAIHarness()
        state = harness.get_state()
        assert state.status == "idle"

    def test_full_lifecycle(self) -> None:
        """Full harness lifecycle: init -> execute -> cleanup."""
        harness = PydanticAIHarness()
        harness.initialize({"run_id": "lifecycle-test"})
        assert harness.get_state().status == "running"

        result = harness.execute_step("planning", {"prompt": "plan"})
        assert result.success is True
        assert harness.get_state().step_count == 1

        harness.cleanup()
        assert harness.get_state().status == "stopped"


class TestHarnessFactory:
    def test_create_pydantic_ai_harness(self) -> None:
        harness = HarnessFactory.create("pydantic-ai", {})
        assert isinstance(harness, PydanticAIHarness)

    def test_create_pydantic_ai_with_orchestrator(self) -> None:
        mock_orch = MagicMock()
        harness = HarnessFactory.create("pydantic-ai", {"orchestrator": mock_orch})
        assert isinstance(harness, PydanticAIHarness)

    def test_create_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown harness type"):
            HarnessFactory.create("unknown-harness", {})

    def test_factory_returns_runtime_harness(self) -> None:
        harness = HarnessFactory.create("pydantic-ai", {})
        assert isinstance(harness, RuntimeHarness)


class TestImports:
    def test_harness_importable_from_agents(self) -> None:
        from openeinstein.agents import HarnessFactory as HF
        from openeinstein.agents import PydanticAIHarness as PAH
        from openeinstein.agents import RuntimeHarness as RH

        assert RH is not None
        assert PAH is not None
        assert HF is not None
