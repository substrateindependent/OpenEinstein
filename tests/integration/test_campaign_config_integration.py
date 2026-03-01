"""Integration tests for campaign config discovery/loading."""

from __future__ import annotations

from pathlib import Path

from openeinstein.campaigns import CampaignConfigLoader


def test_campaign_pack_discovery_and_runtime_validation() -> None:
    loader = CampaignConfigLoader(Path("campaign-packs"))
    packs = loader.discover_packs()
    assert "modified-gravity-action-search" in packs

    loaded = loader.load_pack("modified-gravity-action-search")
    assert loaded.config.name == "modified-gravity-action-search"
    assert loaded.config.gate_pipeline

    backend_capabilities = {
        "mathematica": {"tensor_simplify", "vary_action", "perturbation_expansion"},
        "cadabra": {"tensor_simplify", "vary_action"},
        "sandbox": {"stability_analysis"},
    }
    runtime = loader.validate_runtime_requirements(
        loaded.config,
        backend_capabilities=backend_capabilities,
        available_tools={"registry", "scanner", "literature"},
    )
    assert "capability_map" in runtime
    assert set(runtime["capability_map"]) == {gate.name for gate in loaded.config.gate_pipeline}
