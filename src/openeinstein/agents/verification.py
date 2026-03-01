"""Verification-focused agent for inconsistency detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from openeinstein.agents.base import OpenEinsteinAgent


class VerificationIssue(BaseModel):
    key: str
    values: list[str] = Field(default_factory=list)
    message: str
    severity: str = "high"
    sources: list[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    inconsistent: bool
    review_required: bool
    issues: list[VerificationIssue] = Field(default_factory=list)
    summary: str


class VerificationAgent(OpenEinsteinAgent):
    """Detects logical inconsistencies across claim sets."""

    def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
        claims = kwargs.get("claims", [])
        issues = self.detect_inconsistencies(claims)
        report = VerificationReport(
            inconsistent=bool(issues),
            review_required=bool(issues),
            issues=issues,
            summary=self._summary(issues),
        )
        return report.model_dump()

    @staticmethod
    def detect_inconsistencies(claims: list[dict[str, Any]]) -> list[VerificationIssue]:
        grouped_values: dict[str, set[str]] = defaultdict(set)
        grouped_sources: dict[str, list[str]] = defaultdict(list)
        for claim in claims:
            key = str(claim.get("key", "")).strip()
            if not key:
                continue
            value = str(claim.get("value"))
            source = str(claim.get("source", "unknown"))
            grouped_values[key].add(value)
            grouped_sources[key].append(source)

        issues: list[VerificationIssue] = []
        for key, values in grouped_values.items():
            if len(values) <= 1:
                continue
            issues.append(
                VerificationIssue(
                    key=key,
                    values=sorted(values),
                    message=f"Conflicting values detected for '{key}'",
                    severity="high",
                    sources=sorted(set(grouped_sources[key])),
                )
            )
        return sorted(issues, key=lambda issue: issue.key)

    @staticmethod
    def _summary(issues: list[VerificationIssue]) -> str:
        if not issues:
            return "No inconsistencies detected."
        return f"Detected {len(issues)} inconsistency issue(s) requiring review."
