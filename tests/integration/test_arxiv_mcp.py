"""Integration tests for arXiv MCP server."""

from __future__ import annotations

from pathlib import Path

from conftest import requires_network
from openeinstein.tools import ArxivMCPServer, MCPConnectionManager, ToolBus


@requires_network
def test_arxiv_server_search_and_download(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("arxiv", ArxivMCPServer(tmp_path / "arxiv"))
    bus = ToolBus(manager)

    tools = {spec.name for spec in bus.get_tools("arxiv")}
    assert {"search", "download_pdf", "capabilities"} <= tools

    searched = bus.call(
        "arxiv",
        "search",
        {"query": "quantum gravity", "max_results": 2, "timeout_seconds": 20},
    )
    assert searched.success
    assert searched.output["count"] >= 1

    first_record = searched.output["records"][0]
    assert first_record["arxiv_id"]

    downloaded = bus.call(
        "arxiv",
        "download_pdf",
        {"arxiv_id": first_record["arxiv_id"], "timeout_seconds": 45},
    )
    assert downloaded.success

    pdf_path = Path(downloaded.output["path"])
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1024
