"""Integration tests for lane-aware concurrent campaign execution (Stories 1.3, 1.4)."""

from __future__ import annotations

import time
from pathlib import Path

from openeinstein.campaigns.executor import CampaignExecutor, RuntimeLimits
from openeinstein.campaigns.lanes import LaneConfig, LaneRegistry
from openeinstein.campaigns.state import ConcurrentStepTracker


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


# ── Phase-to-lane mapping ──


def test_lane_mapping_for_phases() -> None:
    """Each step phase maps to a known lane name."""
    from openeinstein.campaigns.executor import _lane_for_phase

    assert _lane_for_phase("planning") == "main"
    assert _lane_for_phase("verifying") == "main"
    assert _lane_for_phase("generating") == "main"
    assert _lane_for_phase("gating") == "main"
    assert _lane_for_phase("literature") == "literature"


# ── Constructor accepts lane_registry ──


def test_executor_accepts_lane_registry(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    configs = {"main": LaneConfig(name="main", max_concurrent=2)}
    registry = LaneRegistry(configs)
    executor = CampaignExecutor(db_path=db_path, lane_registry=registry)
    assert executor._lane_registry is registry
    executor.close()


def test_executor_none_lane_registry(tmp_path: Path) -> None:
    """Executor without lane_registry falls back to serial execution."""
    db_path = tmp_path / "test.db"
    executor = CampaignExecutor(db_path=db_path, lane_registry=None)
    assert executor._lane_registry is None
    executor.close()


# ── Lane acquire/release around step execution ──


def test_lane_semaphore_released_on_success(tmp_path: Path) -> None:
    """After a successful step, the lane semaphore is released."""
    db_path = tmp_path / "test.db"
    configs = {
        "main": LaneConfig(name="main", max_concurrent=2),
        "literature": LaneConfig(name="literature", max_concurrent=1),
    }
    registry = LaneRegistry(configs)
    executor = CampaignExecutor(db_path=db_path, lane_registry=registry)

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=False)

    step = executor.execute_next_step(run_id)
    assert step is not None

    # Lane should be released (active == 0)
    status = registry.lane_status()
    assert status["main"]["active"] == 0

    executor.close()


def test_lane_semaphore_released_on_error(tmp_path: Path) -> None:
    """Verify lane semaphore is released even when a step triggers an error path."""
    db_path = tmp_path / "test.db"
    configs = {"main": LaneConfig(name="main", max_concurrent=1)}
    registry = LaneRegistry(configs)
    executor = CampaignExecutor(
        db_path=db_path,
        lane_registry=registry,
        runtime_limits=RuntimeLimits(max_steps=1, max_cost_usd=0.0),
    )

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=False)
    executor.execute_next_step(run_id)

    # Lane should be released regardless of error
    status = registry.lane_status()
    assert status["main"]["active"] == 0

    executor.close()


# ── Events include lane metadata ──


def test_events_include_lane_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    configs = {
        "main": LaneConfig(name="main", max_concurrent=4),
        "literature": LaneConfig(name="literature", max_concurrent=2),
    }
    registry = LaneRegistry(configs)
    executor = CampaignExecutor(db_path=db_path, lane_registry=registry)

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=False)
    executor.execute_next_step(run_id)

    events = executor.get_events(run_id)
    step_started_events = [e for e in events if e.event_type == "step_started"]
    assert len(step_started_events) >= 1
    first_event = step_started_events[0]
    assert "lane_name" in first_event.payload
    assert "lane_active_count" in first_event.payload

    executor.close()


# ── Backward compatibility: serial when no registry ──


def test_serial_fallback_without_registry(tmp_path: Path) -> None:
    """Executor without lane_registry runs steps sequentially (existing behavior)."""
    db_path = tmp_path / "test.db"
    executor = CampaignExecutor(db_path=db_path)

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=False)
    step = executor.execute_next_step(run_id)
    assert step is not None
    assert step.phase == "planning"

    executor.close()


# ── desired_state=paused halts between lane acquires ──


def test_desired_state_paused_halts_dispatch(tmp_path: Path) -> None:
    """Pausing a run stops execution between lane acquires."""
    db_path = tmp_path / "test.db"
    configs = {"main": LaneConfig(name="main", max_concurrent=4)}
    registry = LaneRegistry(configs)
    executor = CampaignExecutor(db_path=db_path, lane_registry=registry)

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=True)

    # Give executor a moment to start, then pause
    time.sleep(0.1)
    executor.pause_campaign(run_id)

    # Wait for paused state
    try:
        executor.wait_for_status(
            run_id,
            {"paused", "completed", "failed"},
            timeout_seconds=5.0,
        )
    except TimeoutError:
        pass

    # All lanes should be released when paused
    lane_status = registry.lane_status()
    assert lane_status["main"]["active"] == 0

    executor.close()


# ── Story 1.4: ConcurrentStepTracker integration ──


def test_executor_accepts_concurrent_tracker(tmp_path: Path) -> None:
    """Executor accepts optional concurrent_tracker parameter."""
    db_path = tmp_path / "test.db"
    tracker = ConcurrentStepTracker()
    executor = CampaignExecutor(db_path=db_path, concurrent_tracker=tracker)
    assert executor._concurrent_tracker is tracker
    executor.close()


def test_tracker_status_in_step_events(tmp_path: Path) -> None:
    """Step events include tracker_status when tracker is configured."""
    db_path = tmp_path / "test.db"
    tracker = ConcurrentStepTracker()
    executor = CampaignExecutor(db_path=db_path, concurrent_tracker=tracker)

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=False)
    executor.execute_next_step(run_id)

    events = executor.get_events(run_id)
    step_started_events = [e for e in events if e.event_type == "step_started"]
    assert len(step_started_events) >= 1
    first = step_started_events[0]
    assert "tracker_status" in first.payload

    executor.close()


def test_tracker_step_completed_after_execution(tmp_path: Path) -> None:
    """After step execution, tracker has no active steps (step was completed)."""
    db_path = tmp_path / "test.db"
    tracker = ConcurrentStepTracker()
    executor = CampaignExecutor(db_path=db_path, concurrent_tracker=tracker)

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=False)
    executor.execute_next_step(run_id)

    # Tracker should have no active steps after completion
    assert tracker.lane_status == {}

    executor.close()


def test_tracker_step_completed_on_error(tmp_path: Path) -> None:
    """Tracker step is completed even when execution fails."""
    db_path = tmp_path / "test.db"
    tracker = ConcurrentStepTracker()
    executor = CampaignExecutor(
        db_path=db_path,
        concurrent_tracker=tracker,
        runtime_limits=RuntimeLimits(max_steps=1, max_cost_usd=0.0),
    )

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=False)
    executor.execute_next_step(run_id)

    # Tracker should be clean even after error
    assert tracker.lane_status == {}

    executor.close()


def test_executor_without_tracker_still_works(tmp_path: Path) -> None:
    """Executor without concurrent_tracker works normally (backward compat)."""
    db_path = tmp_path / "test.db"
    executor = CampaignExecutor(db_path=db_path)

    campaign_file = _write_campaign(tmp_path)
    run_id = executor.start_campaign(campaign_path=str(campaign_file), auto_run=False)
    step = executor.execute_next_step(run_id)
    assert step is not None
    assert step.phase == "planning"

    executor.close()
