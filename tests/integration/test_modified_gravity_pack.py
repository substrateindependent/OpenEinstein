"""Integration tests for modified-gravity campaign pack dry-run."""

from __future__ import annotations

from pathlib import Path

from openeinstein.campaigns import CampaignConfigLoader, CandidateInput, GatePipelineRunner, TemplateRegistry
from openeinstein.persistence import CampaignDB


def test_modified_gravity_pack_install_validate_and_mock_dry_run(tmp_path: Path) -> None:
    loader = CampaignConfigLoader(Path("campaign-packs"))
    loaded = loader.load_pack("modified-gravity-action-search")

    runtime = loader.validate_runtime_requirements(
        loaded.config,
        backend_capabilities={
            "mathematica": {
                "tensor_simplify",
                "vary_action",
                "perturbation_expansion",
                "stability_analysis",
            },
            "sympy": {"tensor_simplify", "perturbation_expansion"},
        },
        available_tools={"registry", "scanner", "arxiv", "crossref"},
    )
    assert runtime["capability_map"]

    registry = TemplateRegistry()
    loaded_templates = registry.load_directory(loaded.pack_dir / "templates")
    assert loaded_templates >= 3

    db = CampaignDB(tmp_path / ".openeinstein" / "openeinstein.db")

    def execute(_backend: str, _gate, _candidate_data):
        return {"success": True, "backend": _backend, "gate": _gate.name}

    runner = GatePipelineRunner(
        db,
        backend_capabilities={
            "mathematica": {
                "tensor_simplify",
                "vary_action",
                "perturbation_expansion",
                "stability_analysis",
            }
        },
        execute_backend=execute,
    )
    results = runner.run_candidate(
        "pack-dry-run",
        CandidateInput(candidate_key="candidate-1", data={"action_expression": "R + alpha*R**2"}),
        loaded.config.gate_pipeline,
    )
    assert results
    assert all(row.status == "passed" for row in results)
    db.close()
