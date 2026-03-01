"""Adaptive sampling engine for campaign candidate reprioritization."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from openeinstein.persistence import FailureRecord


class SamplingCandidate(BaseModel):
    candidate_key: str = Field(min_length=1)
    priority: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SamplingDecision(BaseModel):
    candidate_key: str
    score: float
    rationale: str


class AdaptiveSampler:
    """Deterministic heuristic sampler driven by failure patterns."""

    def __init__(
        self,
        *,
        candidate_failure_weight: float = 1.5,
        region_failure_weight: float = 0.5,
        exploration_bonus: float = 2.0,
    ) -> None:
        self._candidate_failure_weight = candidate_failure_weight
        self._region_failure_weight = region_failure_weight
        self._exploration_bonus = exploration_bonus

    def reprioritize(
        self,
        candidates: list[SamplingCandidate],
        failures: list[FailureRecord],
    ) -> list[SamplingDecision]:
        by_candidate = Counter(row.candidate_key for row in failures)
        by_region: Counter[str] = Counter()
        for row in failures:
            region = str(row.details.get("region", "")).strip()
            if region:
                by_region[region] += 1

        decisions: list[SamplingDecision] = []
        for candidate in candidates:
            candidate_failures = by_candidate[candidate.candidate_key]
            region = str(candidate.metadata.get("region", "")).strip()
            region_failures = by_region[region] if region else 0
            score = (
                candidate.priority
                - candidate_failures * self._candidate_failure_weight
                - region_failures * self._region_failure_weight
            )
            if candidate_failures == 0:
                score += self._exploration_bonus
            rationale = (
                f"priority={candidate.priority}, candidate_failures={candidate_failures}, "
                f"region_failures={region_failures}"
            )
            decisions.append(
                SamplingDecision(
                    candidate_key=candidate.candidate_key,
                    score=score,
                    rationale=rationale,
                )
            )

        return sorted(decisions, key=lambda row: (-row.score, row.candidate_key))

    def reprioritize_keys(
        self,
        candidates: list[SamplingCandidate],
        failures: list[FailureRecord],
    ) -> list[str]:
        return [row.candidate_key for row in self.reprioritize(candidates, failures)]
