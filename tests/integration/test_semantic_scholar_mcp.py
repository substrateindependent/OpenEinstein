"""Integration tests for Semantic Scholar MCP server."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from conftest import requires_network
from openeinstein.tools import MCPConnectionManager, SemanticScholarMCPServer, ToolBus


def _semantic_scholar_keyless_probe() -> bool:
    request = Request(
        "https://api.semanticscholar.org/graph/v1/paper/search?query=quantum&limit=1&fields=paperId,title",
        headers={
            "Accept": "application/json",
            "User-Agent": "OpenEinstein/0.1 (+https://github.com/open-einstein/openeinstein)",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status == 200
    except HTTPError as exc:
        return exc.code not in {401, 403, 429}
    except URLError:
        return False


@requires_network
def test_semantic_scholar_server_search_and_lookup(tmp_path: Path) -> None:
    api_key = os.getenv("S2_API_KEY", "").strip()
    if not api_key and not _semantic_scholar_keyless_probe():
        pytest.skip("Semantic Scholar keyless probe failed and S2_API_KEY is not set")

    manager = MCPConnectionManager()
    manager.register_server(
        "semantic_scholar",
        SemanticScholarMCPServer(tmp_path / "semantic-scholar"),
    )
    bus = ToolBus(manager)

    tools = {spec.name for spec in bus.get_tools("semantic_scholar")}
    assert {"search", "get_paper", "capabilities"} <= tools

    searched = bus.call(
        "semantic_scholar",
        "search",
        {"query": "quantum gravity", "limit": 2, "timeout_seconds": 20},
    )
    if not searched.success and not api_key and "429" in str(searched.error):
        pytest.skip("Semantic Scholar keyless query rate-limited (HTTP 429)")
    assert searched.success
    assert searched.output["count"] >= 1

    first_record = searched.output["records"][0]
    assert first_record["title"]

    paper_id = first_record.get("paper_id")
    doi = first_record.get("doi")
    if paper_id:
        looked_up = bus.call(
            "semantic_scholar",
            "get_paper",
            {"paper_id": paper_id, "timeout_seconds": 20},
        )
    else:
        assert doi
        looked_up = bus.call(
            "semantic_scholar",
            "get_paper",
            {"doi": doi, "timeout_seconds": 20},
        )

    if not looked_up.success and not api_key and "429" in str(looked_up.error):
        pytest.skip("Semantic Scholar keyless lookup rate-limited (HTTP 429)")
    assert looked_up.success
    assert looked_up.output["paper"]["title"]
