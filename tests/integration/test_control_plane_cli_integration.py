"""Integration tests for run lifecycle CLI commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from openeinstein.cli.main import app


def test_run_cli_lifecycle_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    campaign = tmp_path / "campaign.yaml"
    campaign.write_text("name: sample\n", encoding="utf-8")

    runner = CliRunner()
    started = runner.invoke(app, ["run", "start", str(campaign)])
    assert started.exit_code == 0
    run_id = started.stdout.split("Started run ", maxsplit=1)[1].split(" ", maxsplit=1)[0]

    status = runner.invoke(app, ["run", "status", run_id])
    assert status.exit_code == 0
    assert "running" in status.stdout

    stopped = runner.invoke(app, ["run", "stop", run_id])
    assert stopped.exit_code == 0
    resumed = runner.invoke(app, ["run", "resume", run_id])
    assert resumed.exit_code == 0

    events = runner.invoke(app, ["run", "events", run_id])
    assert events.exit_code == 0
    assert "run_started" in events.stdout
    assert "run_stopped" in events.stdout
    assert "run_resumed" in events.stdout
