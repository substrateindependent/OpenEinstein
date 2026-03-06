"""Quickstart campaign runner qualification (IC-PR-12)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from openeinstein.cli.main import app

pytestmark = pytest.mark.production


def test_quickstart_cli_flow_runs_real_campaign(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    init_result = runner.invoke(app, ["init"])
    assert init_result.exit_code == 0

    campaign = tmp_path / "quickstart-campaign.yaml"
    campaign.write_text(
        "\n".join(
            [
                "campaign:",
                "  name: quickstart",
                "  version: '0.1.0'",
                "  search_space:",
                "    generator_skill: quickstart-skill",
                "  gate_pipeline:",
                "    - name: gate",
                "      skill: gate-skill",
                "      timeout_seconds: 5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    started = runner.invoke(app, ["run", "start", str(campaign)])
    assert started.exit_code == 0

    run_id = started.stdout.split("Started run ", maxsplit=1)[1].split(" ", maxsplit=1)[0]

    waited = runner.invoke(app, ["run", "wait", run_id, "--timeout", "30"])
    assert waited.exit_code == 0

    status = runner.invoke(app, ["run", "status", run_id])
    assert status.exit_code == 0
    assert "completed" in status.stdout or "failed" in status.stdout

    report = runner.invoke(app, ["report", "generate", run_id, "--output", str(tmp_path / "report.md")])
    assert report.exit_code == 0
    assert (tmp_path / "report.md").exists()
