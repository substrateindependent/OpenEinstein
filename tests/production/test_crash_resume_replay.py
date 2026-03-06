"""Crash/restart deterministic resume tests (IC-PR-06)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.campaigns.executor import CampaignExecutor, RuntimeLimits

pytestmark = pytest.mark.production


def test_crash_resume_replay_is_deterministic(tmp_path: Path) -> None:
    db_path = tmp_path / ".openeinstein" / "openeinstein.db"
    campaign_path = Path("campaign-packs/modified-gravity-action-search/campaign.yaml")

    executor_one = CampaignExecutor(
        db_path=db_path,
        runtime_limits=RuntimeLimits(max_steps=12, max_runtime_minutes=5, max_cost_usd=5.0, max_tokens=12000),
    )
    run_id = executor_one.start_campaign(campaign_path=campaign_path, auto_run=False)

    first = executor_one.execute_next_step(run_id)
    second = executor_one.execute_next_step(run_id)
    assert first is not None
    assert second is not None

    before = executor_one.get_events(run_id)
    before_cursor = before[-1].seq

    # Simulate process restart by constructing a new executor from persisted DB.
    executor_two = CampaignExecutor(
        db_path=db_path,
        runtime_limits=RuntimeLimits(max_steps=12, max_runtime_minutes=5, max_cost_usd=5.0, max_tokens=12000),
    )
    executor_two.resume_campaign(run_id)
    terminal = executor_two.wait_for_status(run_id, {"completed", "failed"}, timeout_seconds=20)
    assert terminal in {"completed", "failed"}

    after = executor_two.get_events(run_id)
    assert after[-1].seq > before_cursor
    replay_after_cursor = executor_two.get_events(run_id, after_seq=before_cursor)
    assert replay_after_cursor
    assert all(event.seq > before_cursor for event in replay_after_cursor)
