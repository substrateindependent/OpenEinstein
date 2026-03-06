"""Integration tests for harness + sandbox wiring in the executor (Story 6.3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openeinstein.agents.harness import HarnessFactory, PydanticAIHarness, RuntimeHarness
from openeinstein.campaigns.config import CampaignDefinition
from openeinstein.campaigns.executor import CampaignExecutor


class TestCampaignDefinitionHarnessFields:
    def test_default_harness_type(self) -> None:
        defn = CampaignDefinition(
            name="test",
            version="1.0.0",
            search_space={"generator_skill": "grid_search"},
        )
        assert defn.harness_type == "pydantic-ai"

    def test_custom_harness_type(self) -> None:
        defn = CampaignDefinition(
            name="test",
            version="1.0.0",
            search_space={"generator_skill": "grid_search"},
            harness_type="custom-harness",
        )
        assert defn.harness_type == "custom-harness"

    def test_default_sandbox_mode(self) -> None:
        defn = CampaignDefinition(
            name="test",
            version="1.0.0",
            search_space={"generator_skill": "grid_search"},
        )
        assert defn.sandbox_mode == "isolated"

    def test_sandbox_mode_none(self) -> None:
        defn = CampaignDefinition(
            name="test",
            version="1.0.0",
            search_space={"generator_skill": "grid_search"},
            sandbox_mode="none",
        )
        assert defn.sandbox_mode == "none"


class TestExecutorHarnessIntegration:
    def test_executor_accepts_harness(self, tmp_path: Path) -> None:
        """CampaignExecutor accepts an optional runtime_harness parameter."""
        db_path = tmp_path / "test.db"
        harness = PydanticAIHarness()
        executor = CampaignExecutor(
            db_path=db_path,
            runtime_harness=harness,
        )
        assert executor._runtime_harness is harness

    def test_executor_without_harness_defaults_none(self, tmp_path: Path) -> None:
        """Without explicit harness, executor defaults to None (backward compat)."""
        db_path = tmp_path / "test.db"
        executor = CampaignExecutor(db_path=db_path)
        assert executor._runtime_harness is None

    def test_executor_accepts_sandbox_base(self, tmp_path: Path) -> None:
        """CampaignExecutor accepts an optional sandbox_base_dir parameter."""
        db_path = tmp_path / "test.db"
        sandbox_base = tmp_path / "sandboxes"
        executor = CampaignExecutor(
            db_path=db_path,
            sandbox_base_dir=sandbox_base,
        )
        assert executor._sandbox_base_dir == sandbox_base


class TestHarnessFactoryIntegration:
    def test_factory_creates_valid_harness(self) -> None:
        harness = HarnessFactory.create("pydantic-ai", {})
        assert isinstance(harness, RuntimeHarness)

    def test_factory_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown harness type"):
            HarnessFactory.create("nonexistent", {})

    def test_factory_with_orchestrator(self) -> None:
        mock_orch = MagicMock()
        harness = HarnessFactory.create("pydantic-ai", {"orchestrator": mock_orch})
        harness.initialize({})
        state = harness.get_state()
        assert state.status == "running"


class TestHarnessLifecycle:
    def test_harness_full_lifecycle(self) -> None:
        """Test init -> execute_step -> cleanup lifecycle."""
        harness = PydanticAIHarness()
        harness.initialize({"run_id": "lifecycle-test"})
        assert harness.get_state().status == "running"

        result = harness.execute_step("planning", {"prompt": "plan"})
        assert result.success is True
        assert harness.get_state().step_count == 1
        assert harness.get_state().current_phase == "planning"

        harness.cleanup()
        assert harness.get_state().status == "stopped"

    def test_harness_error_handling(self) -> None:
        """Harness handles orchestrator errors gracefully."""
        mock_orch = MagicMock()
        mock_orch.execute.side_effect = RuntimeError("boom")

        harness = PydanticAIHarness(orchestrator=mock_orch)
        harness.initialize({})
        result = harness.execute_step("generating", {})
        assert result.success is False
        assert "boom" in (result.error or "")
