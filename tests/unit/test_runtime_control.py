"""Unit tests for executor-backed control plane compatibility behavior."""

from __future__ import annotations

from pathlib import Path

from openeinstein.gateway.control_plane import FileBackedControlPlane
from openeinstein.gateway.runtime_control import ExecutorBackedControlPlane


def test_legacy_run_stop_and_event_read_do_not_require_executor_state(tmp_path: Path) -> None:
    control_root = tmp_path / ".openeinstein" / "control-plane"
    db_path = tmp_path / ".openeinstein" / "openeinstein.db"

    legacy = FileBackedControlPlane(control_root)
    run_id = legacy.start_run("run-legacy")
    legacy.emit_event(run_id, "legacy_event", {"source": "compat"})

    control = ExecutorBackedControlPlane(control_root, db_path)

    events = control.get_events(run_id)
    assert any(event.event_type == "legacy_event" for event in events)

    control.stop_run(run_id, reason="legacy-stop")
    assert control.get_status(run_id) == "stopped"
