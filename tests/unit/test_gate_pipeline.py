"""Unit tests for gate pipeline runner."""

from __future__ import annotations

import time
from pathlib import Path

from openeinstein.campaigns import CandidateInput, GatePipelineRunner
from openeinstein.campaigns.config import GateConfig
from openeinstein.persistence import CampaignDB


def _db(tmp_path: Path) -> CampaignDB:
    return CampaignDB(tmp_path / ".openeinstein" / "openeinstein.db")


def test_gate_pipeline_routing_and_gate_failure(tmp_path: Path) -> None:
    db = _db(tmp_path)

    def execute(backend: str, gate: GateConfig, candidate_data: dict[str, object]) -> dict[str, object]:
        if gate.name == "Gate Fail":
            return {"success": False, "error": "constraint violated", "backend": backend}
        return {"success": True, "backend": backend, "payload": candidate_data}

    runner = GatePipelineRunner(
        db,
        backend_capabilities={"sympy": {"symbolic"}, "cadabra": {"tensor"}},
        execute_backend=execute,
    )
    gates = [
        GateConfig(name="Gate Pass", skill="g1", cas_requirements=["tensor"], timeout_seconds=2),
        GateConfig(name="Gate Fail", skill="g2", cas_requirements=["symbolic"], timeout_seconds=2),
    ]
    results = runner.run_candidate(
        "run-gate-1",
        CandidateInput(candidate_key="cand-a", data={"x": 1}),
        gates,
    )
    assert [row.status for row in results] == ["passed", "failed"]
    assert results[0].backend == "cadabra"
    assert results[1].failure_type == "gate_failed"
    assert db.get_failure_log("run-gate-1")
    db.close()


def test_gate_pipeline_timeout_and_missing_capability(tmp_path: Path) -> None:
    db = _db(tmp_path)

    def execute(_backend: str, _gate: GateConfig, _candidate_data: dict[str, object]) -> dict[str, object]:
        time.sleep(0.2)
        return {"success": True}

    runner = GatePipelineRunner(
        db,
        backend_capabilities={"sandbox": {"numeric"}},
        execute_backend=execute,
    )
    timeout_gate = GateConfig(
        name="Slow Gate",
        skill="slow",
        cas_requirements=["numeric"],
        timeout_seconds=0.05,
    )
    timeout_results = runner.run_candidate(
        "run-gate-timeout",
        CandidateInput(candidate_key="cand-time", data={"x": 2}),
        [timeout_gate],
    )
    assert timeout_results[0].status == "timeout"
    assert timeout_results[0].failure_type == "timeout"

    missing_gate = GateConfig(
        name="Missing Capability Gate",
        skill="missing",
        cas_requirements=["tensor_algebra"],
        timeout_seconds=1,
    )
    missing_results = runner.run_candidate(
        "run-gate-missing",
        CandidateInput(candidate_key="cand-missing", data={"x": 3}),
        [missing_gate],
    )
    assert missing_results[0].status == "failed"
    assert missing_results[0].failure_type == "missing_capability"
    db.close()
