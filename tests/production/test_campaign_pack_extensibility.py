"""Campaign pack extensibility tests (IC-PR-02, IC-PR-11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.campaigns.executor import CampaignExecutor, RuntimeLimits

pytestmark = pytest.mark.production


def test_new_pack_runs_without_core_code_changes(tmp_path: Path) -> None:
    pack_dir = tmp_path / "campaign-packs" / "pack-ext"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "campaign.yaml").write_text(
        "\n".join(
            [
                "campaign:",
                "  name: pack-ext",
                "  version: '0.1.0'",
                "  description: test pack",
                "  search_space:",
                "    generator_skill: generated-skill",
                "  dependencies:",
                "    tools: []",
                "  gate_pipeline:",
                "    - name: Local Gate",
                "      skill: local-gate",
                "      cas_requirements: []",
                "      timeout_seconds: 5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    db_path = tmp_path / ".openeinstein" / "openeinstein.db"
    executor = CampaignExecutor(
        db_path=db_path,
        runtime_limits=RuntimeLimits(max_steps=8, max_runtime_minutes=3, max_cost_usd=3.0, max_tokens=9000),
    )
    run_id = executor.start_campaign(campaign_path=pack_dir / "campaign.yaml")
    status = executor.wait_for_status(run_id, {"completed", "failed"}, timeout_seconds=20)
    assert status == "completed"
