"""Campaign report synthesis and export helpers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

from openeinstein.persistence import CampaignDB, CandidateRecord, FailureRecord


class ReportCandidate(BaseModel):
    candidate_key: str
    status: str
    score: float
    backend: str | None = None
    notes: str = ""


class CampaignReport(BaseModel):
    run_id: str
    summary: str
    candidates: list[ReportCandidate] = Field(default_factory=list)
    failures: list[FailureRecord] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class CampaignReportGenerator:
    """Generates Markdown (and optional LaTeX) reports from campaign DB data."""

    def __init__(self, db: CampaignDB) -> None:
        self._db = db

    def synthesize(self, run_id: str) -> CampaignReport:
        candidates = self._db.get_candidates(run_id)
        failures = self._db.get_failure_log(run_id)
        failure_by_candidate = Counter(item.candidate_key for item in failures)

        report_candidates = [self._candidate_to_report(row, failure_by_candidate) for row in candidates]
        report_candidates.sort(key=lambda row: (-row.score, row.candidate_key))

        recommendations = [row.candidate_key for row in report_candidates[:3] if row.status == "pass"]
        if not recommendations and report_candidates:
            recommendations = [report_candidates[0].candidate_key]

        failure_types = Counter(item.failure_type for item in failures)
        open_questions = [
            f"How should we reduce {failure_type} failures?"
            for failure_type, _count in failure_types.most_common(3)
        ]
        if not open_questions:
            open_questions = ["No major open issues detected from current failure logs."]

        summary = (
            f"Run {run_id} evaluated {len(candidates)} candidates with "
            f"{len(failures)} recorded failures."
        )
        return CampaignReport(
            run_id=run_id,
            summary=summary,
            candidates=report_candidates,
            failures=failures,
            recommendations=recommendations,
            open_questions=open_questions,
        )

    def to_markdown(self, report: CampaignReport) -> str:
        lines = [
            f"# Campaign Report: {report.run_id}",
            "",
            "## Executive Summary",
            report.summary,
            "",
            "## Candidate Comparison",
            "| Candidate | Status | Score | Backend | Notes |",
            "|---|---:|---:|---|---|",
        ]
        for candidate in report.candidates:
            lines.append(
                f"| {candidate.candidate_key} | {candidate.status} | {candidate.score:.2f} | "
                f"{candidate.backend or '-'} | {candidate.notes or '-'} |"
            )
        if not report.candidates:
            lines.append("| - | - | - | - | - |")

        lines.extend(
            [
                "",
                "## Failure Analysis",
                f"Total failures: {len(report.failures)}",
            ]
        )
        if report.failures:
            for failure in report.failures[:20]:
                lines.append(
                    f"- `{failure.candidate_key}` `{failure.failure_type}`: "
                    f"{failure.details.get('error', 'n/a')}"
                )
        else:
            lines.append("- No failures recorded.")

        lines.extend(
            [
                "",
                "## Recommended Candidates",
            ]
        )
        for key in report.recommendations:
            lines.append(f"- {key}")
        if not report.recommendations:
            lines.append("- No recommendation available.")

        lines.extend(
            [
                "",
                "## Open Questions",
            ]
        )
        for question in report.open_questions:
            lines.append(f"- {question}")

        lines.append("")
        return "\n".join(lines)

    def write_markdown(self, report: CampaignReport, output: str | Path) -> Path:
        path = Path(output).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(report), encoding="utf-8")
        return path

    def export_latex(self, report: CampaignReport, output: str | Path) -> Path:
        path = Path(output).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        escaped_summary = report.summary.replace("&", "\\&").replace("%", "\\%")
        recommendations = "\n".join(f"\\item {item}" for item in report.recommendations) or "\\item None"
        content = "\n".join(
            [
                r"\documentclass[11pt]{article}",
                r"\usepackage[T1]{fontenc}",
                r"\usepackage{lmodern}",
                r"\begin{document}",
                rf"\section*{{Campaign Report: {report.run_id}}}",
                escaped_summary,
                r"\subsection*{Recommended Candidates}",
                r"\begin{itemize}",
                recommendations,
                r"\end{itemize}",
                r"\end{document}",
                "",
            ]
        )
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def _candidate_to_report(
        row: CandidateRecord,
        failure_counts: Counter[str],
    ) -> ReportCandidate:
        gate_result = row.gate_result or {}
        backend = gate_result.get("backend")
        failure_count = failure_counts[row.candidate_key]
        status = "fail" if failure_count else "pass"
        base_score = 1.0 if status == "pass" else 0.0
        score = base_score - failure_count * 0.5
        notes = str(gate_result.get("error", "")).strip()
        return ReportCandidate(
            candidate_key=row.candidate_key,
            status=status,
            score=score,
            backend=str(backend) if backend else None,
            notes=notes,
        )
