"""Unit tests for control plane lifecycle primitives."""

from __future__ import annotations

import json
from pathlib import Path

from openeinstein.gateway import FileBackedControlPlane, RunEvent


def test_run_lifecycle_and_artifact_attachment(tmp_path: Path) -> None:
    control = FileBackedControlPlane(tmp_path / "control-plane")
    run_id = control.start_run()
    control.emit_event(run_id, "step_started", {"step": "s1"})

    assert control.get_status(run_id) == "running"
    control.stop_run(run_id, reason="test-stop")
    assert control.get_status(run_id) == "stopped"
    waited = control.wait_for_status(run_id, {"stopped"}, timeout_seconds=1.0)
    assert waited == "stopped"
    control.resume_run(run_id)
    assert control.get_status(run_id) == "running"

    artifact_source = tmp_path / "artifact.txt"
    artifact_source.write_text("hello", encoding="utf-8")
    artifact = control.attach_artifact(run_id, "note", artifact_source)
    assert Path(artifact.path).exists()
    assert len(control.list_artifacts(run_id)) == 1


def test_event_stream_schema_conformance(tmp_path: Path) -> None:
    control = FileBackedControlPlane(tmp_path / "control-plane")
    run_id = control.start_run("run-fixed")
    control.emit_event(run_id, "custom_event", {"value": 42})

    jsonl_path = tmp_path / "control-plane" / "events" / "run-fixed.jsonl"
    lines = [line for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) >= 2
    for line in lines:
        payload = json.loads(line)
        event = RunEvent.model_validate(payload)
        assert event.run_id == "run-fixed"
