"""End-to-end production agent loop tests (IC-PR-02, IC-PR-03, IC-PR-10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.campaigns.executor import CampaignExecutor, RuntimeLimits
from openeinstein.persistence import CampaignDB
from openeinstein.reports import CampaignReportGenerator

pytestmark = pytest.mark.production


REQUIRED_PHASES = {"planning", "generating", "gating", "literature", "verifying"}


def test_full_agent_loop_runs_all_major_phases_and_reports(tmp_path: Path) -> None:
    db_path = tmp_path / ".openeinstein" / "openeinstein.db"
    executor = CampaignExecutor(
        db_path=db_path,
        runtime_limits=RuntimeLimits(max_steps=16, max_runtime_minutes=5, max_cost_usd=10.0, max_tokens=24000),
    )

    run_id = executor.start_campaign(
        campaign_path=Path("campaign-packs/modified-gravity-action-search/campaign.yaml"),
        parameters={"seed": "full-loop"},
    )
    status = executor.wait_for_status(run_id, {"completed", "failed"}, timeout_seconds=20)
    assert status in {"completed", "failed"}

    phases = {step.phase for step in executor.get_steps(run_id)}
    assert REQUIRED_PHASES.issubset(phases)

    db = CampaignDB(db_path)
    report = CampaignReportGenerator(db).synthesize(run_id)
    assert report.run_id == run_id
    assert report.summary
    # Either viable recommendations or explicit documented null-result framing.
    assert report.recommendations or report.open_questions
    assert report.failure_map
    assert report.next_steps
    db.close()
