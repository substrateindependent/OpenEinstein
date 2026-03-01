"""Integration tests for adaptive sampling with persisted failure logs."""

from __future__ import annotations

from pathlib import Path

from openeinstein.campaigns import AdaptiveSampler, SamplingCandidate
from openeinstein.persistence import CampaignDB


def test_adaptive_sampling_reads_failure_patterns_from_db(tmp_path: Path) -> None:
    db = CampaignDB(tmp_path / ".openeinstein" / "openeinstein.db")
    run_id = "run-sampling-1"
    db.log_failure(run_id, "cand-3", "timeout", {"region": "infrared"})
    db.log_failure(run_id, "cand-3", "execution_error", {"region": "infrared"})
    db.log_failure(run_id, "cand-2", "gate_failed", {"region": "uv"})
    failures = db.get_failure_log(run_id)

    candidates = [
        SamplingCandidate(candidate_key="cand-1", priority=0.5, metadata={"region": "visible"}),
        SamplingCandidate(candidate_key="cand-2", priority=1.2, metadata={"region": "uv"}),
        SamplingCandidate(candidate_key="cand-3", priority=1.0, metadata={"region": "infrared"}),
    ]
    ordered = AdaptiveSampler().reprioritize_keys(candidates, failures)
    assert ordered[0] == "cand-1"
    assert ordered[-1] == "cand-3"
    db.close()
