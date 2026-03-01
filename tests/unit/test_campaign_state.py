"""Unit tests for campaign state machine behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.campaigns import CampaignStateMachine
from openeinstein.gateway import FileBackedControlPlane
from openeinstein.persistence import CampaignDB


def _build_state_machine(tmp_path: Path) -> CampaignStateMachine:
    db = CampaignDB(tmp_path / ".openeinstein" / "openeinstein.db")
    control = FileBackedControlPlane(tmp_path / ".openeinstein" / "control-plane")
    return CampaignStateMachine(db, control)


def test_campaign_state_machine_transitions_and_idempotency(tmp_path: Path) -> None:
    machine = _build_state_machine(tmp_path)
    run_id = machine.initialize_run(metadata={"seed": 1})

    running = machine.transition(run_id, "running")
    assert running.state == "running"

    first = machine.record_candidate(
        run_id,
        candidate_key="cand-1",
        candidate_data={"x": 1},
        gate_name="gate-a",
    )
    assert first.created is True

    second = machine.record_candidate(
        run_id,
        candidate_key="cand-1",
        candidate_data={"x": 1},
        gate_name="gate-a",
    )
    assert second.created is False
    assert second.candidate_id == first.candidate_id

    checkpointed = machine.checkpoint(run_id, {"cursor": 5})
    assert checkpointed.metadata["checkpoint"]["cursor"] == 5


def test_campaign_state_machine_invalid_transition_raises(tmp_path: Path) -> None:
    machine = _build_state_machine(tmp_path)
    run_id = machine.initialize_run()
    machine.transition(run_id, "running")
    machine.transition(run_id, "completed")
    with pytest.raises(ValueError, match="Invalid transition"):
        machine.transition(run_id, "running")
