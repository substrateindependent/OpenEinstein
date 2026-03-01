"""Integration tests for INSPIRE connector server."""

from __future__ import annotations

from pathlib import Path

from conftest import requires_network
from openeinstein.tools import InspireMCPServer, MCPConnectionManager, ToolBus


@requires_network
def test_inspire_search_author_and_citation_export(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("inspire", InspireMCPServer(tmp_path / "inspire"))
    bus = ToolBus(manager)

    tools = {spec.name for spec in bus.get_tools("inspire")}
    assert {"search_literature", "lookup_author", "export_citations", "capabilities"} <= tools

    searched = bus.call(
        "inspire",
        "search_literature",
        {"query": "quantum gravity", "size": 2, "timeout_seconds": 20},
    )
    assert searched.success
    assert searched.output["count"] >= 1

    first_record = searched.output["records"][0]
    assert first_record["record_id"]
    assert first_record["title"]

    authors = bus.call(
        "inspire",
        "lookup_author",
        {"query": "Einstein", "size": 1, "timeout_seconds": 20},
    )
    assert authors.success
    assert authors.output["count"] >= 1
    assert authors.output["records"][0]["name"]

    citations = bus.call(
        "inspire",
        "export_citations",
        {"record_id": first_record["record_id"], "size": 2, "timeout_seconds": 20},
    )
    assert citations.success
    assert "citations" in citations.output
