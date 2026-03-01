"""Integration tests for report generation CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from openeinstein.cli.main import app
from openeinstein.gateway import FileBackedControlPlane
from openeinstein.persistence import CampaignDB


def test_report_generation_cli_outputs_markdown_and_latex(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    db = CampaignDB(tmp_path / ".openeinstein" / "openeinstein.db")
    control = FileBackedControlPlane(tmp_path / ".openeinstein" / "control-plane")
    run_id = control.start_run("run-report-cli")
    candidate_id = db.add_candidate(run_id, "cand-1", {"m": 1})
    db.update_gate_result(candidate_id, {"backend": "sympy", "success": True})
    db.log_failure(run_id, "cand-2", "gate_failed", {"error": "constraint"})
    db.close()

    runner = CliRunner()
    md_path = tmp_path / "campaign-report.md"
    tex_path = tmp_path / "campaign-report.tex"
    result = runner.invoke(
        app,
        [
            "report",
            "generate",
            "latest",
            "--output",
            str(md_path),
            "--latex-output",
            str(tex_path),
        ],
    )
    assert result.exit_code == 0
    assert md_path.exists()
    assert tex_path.exists()
    markdown = md_path.read_text(encoding="utf-8")
    assert "## Candidate Comparison" in markdown
    assert "## Failure Analysis" in markdown
