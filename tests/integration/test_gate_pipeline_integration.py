"""Integration tests for gate pipeline runner end-to-end wiring."""

from __future__ import annotations

from pathlib import Path

from openeinstein.campaigns import CandidateInput, GatePipelineRunner
from openeinstein.campaigns.config import GateConfig
from openeinstein.persistence import CampaignDB


def test_gate_pipeline_batch_routing_and_persistence(tmp_path: Path) -> None:
    db = CampaignDB(tmp_path / ".openeinstein" / "openeinstein.db")
    backend_calls: list[str] = []

    def execute(backend: str, gate: GateConfig, candidate_data: dict[str, object]) -> dict[str, object]:
        backend_calls.append(f"{gate.name}:{backend}")
        return {"success": True, "gate": gate.name, "backend": backend, "candidate": candidate_data}

    runner = GatePipelineRunner(
        db,
        backend_capabilities={
            "cadabra": {"tensor"},
            "sympy": {"symbolic"},
        },
        execute_backend=execute,
    )
    gates = [
        GateConfig(name="Tensor Gate", skill="tensor-skill", cas_requirements=["tensor"]),
        GateConfig(name="Symbolic Gate", skill="sym-skill", cas_requirements=["symbolic"]),
    ]
    outputs = runner.run_batch(
        "run-batch-1",
        [
            CandidateInput(candidate_key="cand-1", data={"m": 1}),
            CandidateInput(candidate_key="cand-2", data={"m": 2}),
        ],
        gates,
    )
    assert set(outputs) == {"cand-1", "cand-2"}
    assert all(result[-1].status == "passed" for result in outputs.values())
    assert "Tensor Gate:cadabra" in backend_calls
    assert "Symbolic Gate:sympy" in backend_calls
    assert len(db.get_candidates("run-batch-1")) == 2
    db.close()
