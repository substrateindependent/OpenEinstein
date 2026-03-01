"""Integration tests for Campaign Registry MCP-style server."""

from __future__ import annotations

from pathlib import Path

from openeinstein.tools import CampaignRegistryServer, MCPConnectionManager, ToolBus


def test_registry_server_roundtrip_via_tool_bus(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    server = CampaignRegistryServer(tmp_path / "registry.db")
    manager.register_server("registry", server)
    bus = ToolBus(manager)

    discovered = bus.get_tools("registry")
    names = {spec.name for spec in discovered}
    assert names == {
        "add_candidate",
        "update_gate_result",
        "get_candidates",
        "get_failure_log",
        "get_statistics",
    }

    added = bus.call(
        "registry",
        "add_candidate",
        {"run_id": "run-registry", "candidate_key": "cand-1", "data": {"m": 1}},
    )
    assert added.success
    candidate_id = int(added.output["candidate_id"])

    updated = bus.call(
        "registry",
        "update_gate_result",
        {"candidate_id": candidate_id, "gate_result": {"passed": True}},
    )
    assert updated.success
    assert updated.output == {"updated": True}

    candidates = bus.call("registry", "get_candidates", {"run_id": "run-registry"})
    assert candidates.success
    assert candidates.output[0]["candidate_key"] == "cand-1"
    assert candidates.output[0]["gate_result"] == {"passed": True}

    failures = bus.call("registry", "get_failure_log", {"run_id": "run-registry"})
    assert failures.success
    assert failures.output == []

    stats = bus.call("registry", "get_statistics", {"run_id": "run-registry"})
    assert stats.success
    assert stats.output["candidates"] == 1

    invalid = bus.call("registry", "get_candidates", {})
    assert invalid.success is False
    assert invalid.error is not None
