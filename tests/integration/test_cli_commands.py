"""Integration tests for broad CLI command surface."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from openeinstein.cli.main import app


def test_cli_command_surface_and_campaign_clean(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    help_output = runner.invoke(app, ["--help"])
    assert help_output.exit_code == 0
    assert "OpenEinstein control plane CLI" in help_output.stdout

    init_output = runner.invoke(app, ["init"])
    assert init_output.exit_code == 0
    assert (tmp_path / ".openeinstein").exists()

    campaign_path = tmp_path / "test-campaign.yaml"
    campaign_path.write_text(
        """
campaign:
  name: test-campaign
  version: "0.1.0"
  search_space:
    generator_skill: seed
  gate_pipeline: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    started = runner.invoke(app, ["run", "start", str(campaign_path)])
    assert started.exit_code == 0
    assert "Started run" in started.stdout

    status = runner.invoke(app, ["run", "status", "latest"])
    assert status.exit_code == 0
    assert "Run" in status.stdout

    stopped = runner.invoke(app, ["run", "stop", "latest"])
    assert stopped.exit_code == 0

    waited = runner.invoke(app, ["run", "wait", "latest", "--timeout", "2"])
    assert waited.exit_code == 0
    assert "terminal status" in waited.stdout

    summary = runner.invoke(app, ["results", "latest"])
    assert summary.exit_code == 0
    assert "candidates" in summary.stdout

    exported_path = tmp_path / "export.json"
    exported = runner.invoke(app, ["export", "latest", "--output", str(exported_path)])
    assert exported.exit_code == 0
    assert exported_path.exists()

    repo_root = Path(__file__).resolve().parents[2]
    config_validate = runner.invoke(
        app,
        [
            "config",
            "--validate",
            "--path",
            str(repo_root / "configs" / "openeinstein.example.yaml"),
        ],
    )
    assert config_validate.exit_code == 0
    assert "validation passed" in config_validate.stdout

    sandbox = runner.invoke(app, ["sandbox", "explain", "network access blocked"])
    assert sandbox.exit_code == 0
    assert "network access is disabled" in sandbox.stdout.lower()

    pack_list = runner.invoke(
        app,
        ["pack", "list", "--packs-root", str(repo_root / "campaign-packs")],
    )
    assert pack_list.exit_code == 0
    assert "modified-gravity-action-search" in pack_list.stdout

    cleaned = runner.invoke(app, ["campaign", "clean", "--yes"])
    assert cleaned.exit_code == 0
    assert not (tmp_path / ".openeinstein").exists()
