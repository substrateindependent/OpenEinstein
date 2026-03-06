"""Production lifecycle contract tests (IC-PR-01, IC-PR-06, IC-PR-08)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.campaigns.executor import CampaignExecutor, RuntimeLimits

pytestmark = pytest.mark.production


ALLOWED_RUNTIME_STATES = {
    "queued",
    "planning",
    "generating",
    "gating",
    "literature",
    "verifying",
    "paused",
    "stopped",
    "completed",
    "failed",
}


def test_executor_lifecycle_and_event_replay_contract(tmp_path: Path) -> None:
    db_path = tmp_path / ".openeinstein" / "openeinstein.db"
    executor = CampaignExecutor(
        db_path=db_path,
        runtime_limits=RuntimeLimits(max_steps=12, max_runtime_minutes=5, max_cost_usd=5.0, max_tokens=12000),
    )

    campaign_path = Path("campaign-packs/modified-gravity-action-search/campaign.yaml")
    run_id = executor.start_campaign(campaign_path=campaign_path, parameters={"seed": "production-lifecycle"})

    terminal = executor.wait_for_status(run_id, {"completed", "failed"}, timeout_seconds=20)
    assert terminal in {"completed", "failed"}

    run = executor.get_run(run_id)
    assert run.status in ALLOWED_RUNTIME_STATES

    events = executor.get_events(run_id)
    assert events
    seqs = [event.seq for event in events]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs))

    replay = executor.get_events(run_id, after_seq=events[0].seq)
    assert all(event.seq > events[0].seq for event in replay)

    steps = executor.get_steps(run_id)
    assert steps
    assert all(step.phase in ALLOWED_RUNTIME_STATES for step in steps)
