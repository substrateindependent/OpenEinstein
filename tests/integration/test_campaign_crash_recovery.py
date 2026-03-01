"""Crash-recovery integration coverage across campaign states."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.campaigns import CampaignStateMachine
from openeinstein.gateway import FileBackedControlPlane
from openeinstein.persistence import CampaignDB


STATE_PATHS = {
    "initialized": [],
    "running": ["running"],
    "generating": ["running", "generating"],
    "gating": ["running", "generating", "gating"],
    "stopped": ["running", "stopped"],
}


@pytest.mark.parametrize("target_state", sorted(STATE_PATHS))
def test_campaign_crash_recovery_for_each_state(tmp_path: Path, target_state: str) -> None:
    db_path = tmp_path / ".openeinstein" / "openeinstein.db"
    cp_root = tmp_path / ".openeinstein" / "control-plane"

    db_one = CampaignDB(db_path)
    control_one = FileBackedControlPlane(cp_root)
    machine_one = CampaignStateMachine(db_one, control_one)
    run_id = machine_one.initialize_run(metadata={"state_target": target_state})

    for transition in STATE_PATHS[target_state]:
        machine_one.transition(run_id, transition)  # type: ignore[arg-type]

    machine_one.checkpoint(run_id, {"cursor": 3, "state": target_state})
    machine_one.record_candidate(
        run_id,
        candidate_key=f"cand-{target_state}",
        candidate_data={"state": target_state},
        gate_name="checkpoint",
    )
    pre_crash_candidates = len(db_one.get_candidates(run_id))
    db_one.close()

    db_two = CampaignDB(db_path)
    control_two = FileBackedControlPlane(cp_root)
    machine_two = CampaignStateMachine(db_two, control_two)
    resumed = machine_two.resume(run_id)

    assert resumed.state == target_state
    assert resumed.metadata["checkpoint"]["state"] == target_state
    assert len(db_two.get_candidates(run_id)) == pre_crash_candidates
    db_two.close()
