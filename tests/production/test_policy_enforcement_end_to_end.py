"""Policy/approval enforcement tests for production runner (IC-PR-07)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.campaigns.executor import CampaignExecutor, RuntimeLimits
from openeinstein.security import ApprovalsStore

pytestmark = pytest.mark.production


def test_risky_action_blocked_without_approval_then_allowed_with_grant(tmp_path: Path) -> None:
    db_path = tmp_path / ".openeinstein" / "openeinstein.db"
    approvals_path = tmp_path / ".openeinstein" / "approvals.json"
    approvals = ApprovalsStore(approvals_path)

    executor = CampaignExecutor(
        db_path=db_path,
        approvals_store=approvals,
        runtime_limits=RuntimeLimits(max_steps=8, max_runtime_minutes=5, max_cost_usd=5.0, max_tokens=12000),
    )

    run_blocked = executor.start_campaign(
        campaign_path=Path("campaign-packs/modified-gravity-action-search/campaign.yaml"),
        parameters={"trigger_risky_action": True},
    )
    status_blocked = executor.wait_for_status(run_blocked, {"failed", "stopped", "completed"}, timeout_seconds=20)
    assert status_blocked == "failed"
    assert any(event.event_type == "policy_blocked" for event in executor.get_events(run_blocked))

    approvals.grant("network_fetch")
    run_allowed = executor.start_campaign(
        campaign_path=Path("campaign-packs/modified-gravity-action-search/campaign.yaml"),
        parameters={"trigger_risky_action": True},
    )
    status_allowed = executor.wait_for_status(run_allowed, {"completed", "failed"}, timeout_seconds=20)
    assert status_allowed == "completed"
