"""Integration tests for NASA ADS connector server."""

from __future__ import annotations

from pathlib import Path

from conftest import requires_ads_key, requires_network
from openeinstein.tools import ADSMCPServer, MCPConnectionManager, ToolBus


@requires_network
@requires_ads_key
def test_ads_server_search_and_metrics(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("ads", ADSMCPServer(tmp_path / "ads"))
    bus = ToolBus(manager)

    tools = {spec.name for spec in bus.get_tools("ads")}
    assert {"search", "citation_metrics", "capabilities"} <= tools

    searched = bus.call(
        "ads",
        "search",
        {"query": "quantum gravity", "rows": 1, "timeout_seconds": 20},
    )
    assert searched.success
    assert searched.output["count"] >= 1

    first_record = searched.output["records"][0]
    assert first_record["bibcode"]

    metrics = bus.call(
        "ads",
        "citation_metrics",
        {"bibcode": first_record["bibcode"], "timeout_seconds": 20},
    )
    assert metrics.success
    assert metrics.output["metrics"]["total_citations"] >= 0
