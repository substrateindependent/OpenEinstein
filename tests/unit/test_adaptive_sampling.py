"""Unit tests for adaptive sampling heuristics."""

from __future__ import annotations

from openeinstein.campaigns import AdaptiveSampler, SamplingCandidate
from openeinstein.persistence import FailureRecord


def test_adaptive_sampling_deterministic_reordering() -> None:
    sampler = AdaptiveSampler()
    candidates = [
        SamplingCandidate(candidate_key="cand-a", priority=1.0, metadata={"region": "r1"}),
        SamplingCandidate(candidate_key="cand-b", priority=1.0, metadata={"region": "r2"}),
        SamplingCandidate(candidate_key="cand-c", priority=0.5, metadata={"region": "r1"}),
    ]
    failures = [
        FailureRecord(
            id=1,
            run_id="run-1",
            candidate_key="cand-a",
            failure_type="timeout",
            details={"region": "r1"},
        ),
        FailureRecord(
            id=2,
            run_id="run-1",
            candidate_key="cand-a",
            failure_type="gate_failed",
            details={"region": "r1"},
        ),
    ]
    ordered = sampler.reprioritize_keys(candidates, failures)
    assert ordered == ["cand-b", "cand-c", "cand-a"]
