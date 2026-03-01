"""Unit tests for campaign report generation."""

from __future__ import annotations

from pathlib import Path

from openeinstein.persistence import CampaignDB
from openeinstein.reports import CampaignReportGenerator


def test_report_generation_completeness_and_readability(tmp_path: Path) -> None:
    db = CampaignDB(tmp_path / ".openeinstein" / "openeinstein.db")
    run_id = "run-report-1"
    candidate_id = db.add_candidate(run_id, "cand-1", {"x": 1})
    db.update_gate_result(candidate_id, {"backend": "sympy", "success": True})
    db.log_failure(run_id, "cand-2", "timeout", {"error": "gate timeout"})

    generator = CampaignReportGenerator(db)
    report = generator.synthesize(run_id)
    markdown = generator.to_markdown(report)
    assert "## Executive Summary" in markdown
    assert "## Candidate Comparison" in markdown
    assert "## Failure Analysis" in markdown
    assert "## Recommended Candidates" in markdown
    assert "## Open Questions" in markdown

    tex_path = generator.export_latex(report, tmp_path / "report.tex")
    assert tex_path.exists()
    assert "\\section*" in tex_path.read_text(encoding="utf-8")
    db.close()
