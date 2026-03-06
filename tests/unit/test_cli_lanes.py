"""Unit tests for CLI lane controls (Story 1.5)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from openeinstein.campaigns.executor import CampaignExecutor, RuntimeLimits
from openeinstein.campaigns.lanes import LaneConfig, LaneRegistry
from openeinstein.cli.main import app

runner = CliRunner()


def _write_campaign(tmp_path: Path) -> Path:
    """Helper: write a minimal campaign.yaml and return its path."""
    campaign_dir = tmp_path / "test-campaign"
    campaign_dir.mkdir(exist_ok=True)
    campaign_file = campaign_dir / "campaign.yaml"
    campaign_file.write_text(
        "\n".join([
            "campaign:",
            "  name: test",
            "  version: '0.1.0'",
            "  search_space:",
            "    generator_skill: test-search",
            "",
        ]),
        encoding="utf-8",
    )
    return campaign_file


# ── RuntimeLimits parallel_lanes field ──


def test_runtime_limits_parallel_lanes_default_none() -> None:
    """RuntimeLimits defaults parallel_lanes to None."""
    limits = RuntimeLimits()
    assert limits.parallel_lanes is None


def test_runtime_limits_parallel_lanes_accepts_positive() -> None:
    limits = RuntimeLimits(parallel_lanes=4)
    assert limits.parallel_lanes == 4


def test_runtime_limits_parallel_lanes_accepts_one() -> None:
    limits = RuntimeLimits(parallel_lanes=1)
    assert limits.parallel_lanes == 1


def test_runtime_limits_parallel_lanes_rejects_zero() -> None:
    """parallel_lanes=0 is rejected (must be >= 1)."""
    with pytest.raises(ValueError):
        RuntimeLimits(parallel_lanes=0)


def test_runtime_limits_parallel_lanes_rejects_negative() -> None:
    with pytest.raises(ValueError):
        RuntimeLimits(parallel_lanes=-1)


# ── Executor auto-creates lane registry from parallel_lanes ──


def test_executor_creates_lane_registry_from_parallel_lanes(tmp_path: Path) -> None:
    """When parallel_lanes is set and no lane_registry provided, executor creates one."""
    db_path = tmp_path / "test.db"
    limits = RuntimeLimits(parallel_lanes=3)
    executor = CampaignExecutor(db_path=db_path, runtime_limits=limits)
    assert executor._lane_registry is not None
    assert "main" in executor._lane_registry.lane_names
    executor.close()


def test_executor_explicit_registry_overrides_parallel_lanes(tmp_path: Path) -> None:
    """Explicit lane_registry takes precedence over parallel_lanes."""
    db_path = tmp_path / "test.db"
    configs = {"main": LaneConfig(name="main", max_concurrent=2)}
    registry = LaneRegistry(configs)
    limits = RuntimeLimits(parallel_lanes=8)
    executor = CampaignExecutor(db_path=db_path, runtime_limits=limits, lane_registry=registry)
    assert executor._lane_registry is registry
    executor.close()


def test_executor_no_parallel_lanes_no_auto_registry(tmp_path: Path) -> None:
    """Without parallel_lanes and no lane_registry, executor has no registry."""
    db_path = tmp_path / "test.db"
    executor = CampaignExecutor(db_path=db_path)
    assert executor._lane_registry is None
    executor.close()


# ── Executor.get_lane_status() ──


def test_executor_get_lane_status_with_registry(tmp_path: Path) -> None:
    """get_lane_status returns lane info from the registry."""
    db_path = tmp_path / "test.db"
    configs = {
        "main": LaneConfig(name="main", max_concurrent=4),
        "literature": LaneConfig(name="literature", max_concurrent=2),
    }
    registry = LaneRegistry(configs)
    executor = CampaignExecutor(db_path=db_path, lane_registry=registry)
    status = executor.get_lane_status()
    assert "main" in status
    assert status["main"]["max"] == 4
    assert status["main"]["active"] == 0
    assert "literature" in status
    assert status["literature"]["max"] == 2
    executor.close()


def test_executor_get_lane_status_no_registry(tmp_path: Path) -> None:
    """get_lane_status returns empty dict when no lanes configured."""
    db_path = tmp_path / "test.db"
    executor = CampaignExecutor(db_path=db_path)
    status = executor.get_lane_status()
    assert status == {}
    executor.close()


# ── CLI --parallel-lanes flag on run start ──


def test_cli_run_start_parallel_lanes_flag_parsed(tmp_path: Path) -> None:
    """--parallel-lanes flag is parsed and passed to control plane."""
    campaign_file = _write_campaign(tmp_path)

    mock_control = MagicMock()
    mock_control.start_run.return_value = "run-test123"

    captured_limits: list[RuntimeLimits | None] = []

    def mock_control_plane(runtime_limits: RuntimeLimits | None = None) -> MagicMock:
        captured_limits.append(runtime_limits)
        return mock_control

    with patch("openeinstein.cli.main._control_plane", side_effect=mock_control_plane):
        result = runner.invoke(
            app, ["run", "start", str(campaign_file), "--parallel-lanes", "6"]
        )

    assert result.exit_code == 0, result.output
    assert len(captured_limits) == 1
    assert captured_limits[0] is not None
    assert captured_limits[0].parallel_lanes == 6


def test_cli_run_start_without_parallel_lanes(tmp_path: Path) -> None:
    """run start without --parallel-lanes passes None runtime_limits."""
    campaign_file = _write_campaign(tmp_path)

    mock_control = MagicMock()
    mock_control.start_run.return_value = "run-test123"

    captured_limits: list[RuntimeLimits | None] = []

    def mock_control_plane(runtime_limits: RuntimeLimits | None = None) -> MagicMock:
        captured_limits.append(runtime_limits)
        return mock_control

    with patch("openeinstein.cli.main._control_plane", side_effect=mock_control_plane):
        result = runner.invoke(app, ["run", "start", str(campaign_file)])

    assert result.exit_code == 0, result.output
    assert len(captured_limits) == 1
    assert captured_limits[0] is None


def test_cli_run_start_parallel_lanes_zero_rejected(tmp_path: Path) -> None:
    """--parallel-lanes 0 is rejected at CLI level."""
    campaign_file = _write_campaign(tmp_path)
    result = runner.invoke(
        app, ["run", "start", str(campaign_file), "--parallel-lanes", "0"]
    )
    assert result.exit_code != 0


# ── CLI run status includes lane status ──


def test_cli_run_status_shows_lane_info() -> None:
    """run status output includes lane status when lanes are configured."""
    mock_control = MagicMock()
    mock_control.get_status.return_value = "running"
    mock_control.get_lane_status.return_value = {
        "main": {"active": 1, "max": 4},
        "literature": {"active": 0, "max": 2},
    }

    with patch("openeinstein.cli.main._control_plane", return_value=mock_control), \
         patch("openeinstein.cli.main._resolve_run_id", return_value="run-abc123"):
        result = runner.invoke(app, ["run", "status", "run-abc123"])

    assert result.exit_code == 0
    assert "run-abc123" in result.output
    assert "main" in result.output
    assert "literature" in result.output


def test_cli_run_status_no_lanes_graceful() -> None:
    """run status works when no lanes configured (graceful fallback)."""
    mock_control = MagicMock()
    mock_control.get_status.return_value = "running"
    mock_control.get_lane_status.return_value = {}

    with patch("openeinstein.cli.main._control_plane", return_value=mock_control), \
         patch("openeinstein.cli.main._resolve_run_id", return_value="run-abc123"):
        result = runner.invoke(app, ["run", "status", "run-abc123"])

    assert result.exit_code == 0
    assert "run-abc123" in result.output


# ── Control plane wiring ──


def test_control_plane_accepts_runtime_limits_parameter() -> None:
    """ExecutorBackedControlPlane.__init__ accepts runtime_limits parameter."""
    import inspect

    from openeinstein.gateway.runtime_control import ExecutorBackedControlPlane

    sig = inspect.signature(ExecutorBackedControlPlane.__init__)
    assert "runtime_limits" in sig.parameters


def test_control_plane_get_lane_status_method_exists() -> None:
    """ExecutorBackedControlPlane has get_lane_status method."""
    from openeinstein.gateway.runtime_control import ExecutorBackedControlPlane

    assert hasattr(ExecutorBackedControlPlane, "get_lane_status")
