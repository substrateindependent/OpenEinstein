"""Integration tests for CrossRef MCP server."""

from __future__ import annotations

from pathlib import Path

from conftest import requires_network
from openeinstein.tools import CrossrefMCPServer, MCPConnectionManager, ToolBus


@requires_network
def test_crossref_doi_resolution_roundtrip(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("crossref", CrossrefMCPServer(tmp_path / "crossref"))
    bus = ToolBus(manager)

    tools = {spec.name for spec in bus.get_tools("crossref")}
    assert {"resolve_doi", "search_works", "capabilities"} <= tools

    resolved = bus.call(
        "crossref",
        "resolve_doi",
        {"doi": "10.1038/nphys1170", "timeout_seconds": 20},
    )
    assert resolved.success
    assert resolved.output["record"]["doi"].lower() == "10.1038/nphys1170"
    assert resolved.output["record"]["title"]

    searched = bus.call(
        "crossref",
        "search_works",
        {"query": "quantum gravity", "rows": 2, "timeout_seconds": 20},
    )
    assert searched.success
    assert searched.output["count"] >= 1
