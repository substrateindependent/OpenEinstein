"""Integration tests for campaign state crash-restart behavior."""

from __future__ import annotations

from pathlib import Path

from openeinstein.campaigns import CampaignStateMachine
from openeinstein.gateway import FileBackedControlPlane
from openeinstein.persistence import CampaignDB


def test_campaign_state_crash_restart_resume(tmp_path: Path) -> None:
    db_path = tmp_path / ".openeinstein" / "openeinstein.db"
    cp_root = tmp_path / ".openeinstein" / "control-plane"

    db_one = CampaignDB(db_path)
    control_one = FileBackedControlPlane(cp_root)
    machine_one = CampaignStateMachine(db_one, control_one)

    run_id = machine_one.initialize_run()
    machine_one.transition(run_id, "running")
    machine_one.record_candidate(
        run_id,
        candidate_key="cand-1",
        candidate_data={"value": 42},
        gate_name="cosmo",
    )
    machine_one.checkpoint(run_id, {"cursor": 1, "stage": "gating"})
    db_one.close()

    db_two = CampaignDB(db_path)
    control_two = FileBackedControlPlane(cp_root)
    machine_two = CampaignStateMachine(db_two, control_two)
    resumed = machine_two.resume(run_id)
    assert resumed.state == "running"
    assert resumed.metadata["checkpoint"]["cursor"] == 1
    assert resumed.metadata["checkpoint"]["stage"] == "gating"

    completed = machine_two.transition(run_id, "completed")
    assert completed.state == "completed"
    db_two.close()
