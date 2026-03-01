"""Integration tests for security-related CLI commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from openeinstein.cli.main import app


def test_approvals_and_scan_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    listed = runner.invoke(app, ["approvals", "list"])
    assert listed.exit_code == 0
    assert "No granted approvals." in listed.stdout

    granted = runner.invoke(app, ["approvals", "grant", "shell_exec"])
    assert granted.exit_code == 0
    assert "Granted approval" in granted.stdout

    listed_after_grant = runner.invoke(app, ["approvals", "list"])
    assert listed_after_grant.exit_code == 0
    assert "shell_exec" in listed_after_grant.stdout

    revoked = runner.invoke(app, ["approvals", "revoke", "shell_exec"])
    assert revoked.exit_code == 0
    reset = runner.invoke(app, ["approvals", "reset"])
    assert reset.exit_code == 0

    risky = tmp_path / "risky.py"
    risky.write_text("import os\nos.system('echo bad')\n", encoding="utf-8")
    scan = runner.invoke(app, ["scan", str(risky)])
    assert scan.exit_code == 1
    assert "OS_SYSTEM" in scan.stdout
