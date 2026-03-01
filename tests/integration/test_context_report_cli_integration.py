"""Integration test for context report CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from openeinstein.cli.main import app


def test_context_report_cli(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills" / "alpha"
    skills_root.mkdir(parents=True, exist_ok=True)
    (skills_root / "SKILL.md").write_text(
        "# Alpha\nAlpha context payload\n", encoding="utf-8"
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "context",
            "report",
            "--skills-root",
            str(tmp_path / "skills"),
            "--skill",
            "alpha",
        ],
    )
    assert result.exit_code == 0
    assert "Selected skills: alpha" in result.stdout
    assert "Included files: 1" in result.stdout
