"""Integration tests for tracing CLI wiring."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from openeinstein.cli.main import app
from openeinstein.persistence import CampaignDB
from openeinstein.tracing import TraceStore


def test_trace_cli_list_and_export_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / ".openeinstein" / "openeinstein.db"
    store = TraceStore(CampaignDB(db_path))
    store.record_span(
        run_id="run-cli",
        span_name="seed",
        attributes={"status": "ok"},
        started_at="1",
        ended_at="2",
    )

    runner = CliRunner()
    listed = runner.invoke(app, ["trace", "list", "run-cli"])
    assert listed.exit_code == 0
    assert "seed" in listed.stdout

    output_path = tmp_path / "trace-export.json"
    exported = runner.invoke(
        app, ["trace", "export", "run-cli", "--output", str(output_path)]
    )
    assert exported.exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["name"] == "seed"
