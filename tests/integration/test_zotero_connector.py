"""Integration tests for Zotero connector server."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from conftest import requires_network, requires_zotero_key
from openeinstein.tools import MCPConnectionManager, ToolBus, ZoteroMCPServer


@requires_network
@requires_zotero_key
def test_zotero_sync_and_bibtex_export(tmp_path: Path) -> None:
    if not os.getenv("ZOTERO_USER_ID", "").strip():
        pytest.skip("ZOTERO_USER_ID is not set")

    manager = MCPConnectionManager()
    manager.register_server("zotero", ZoteroMCPServer(tmp_path / "zotero"))
    bus = ToolBus(manager)

    tools = {spec.name for spec in bus.get_tools("zotero")}
    assert {"sync_library", "export_bibtex", "capabilities"} <= tools

    synced = bus.call("zotero", "sync_library", {"limit": 5, "timeout_seconds": 20})
    assert synced.success
    assert synced.output["count"] >= 0

    records = synced.output["records"]
    if records:
        first_key = records[0]["key"]
        exported = bus.call(
            "zotero",
            "export_bibtex",
            {"item_keys": [first_key], "timeout_seconds": 20},
        )
        assert exported.success
        assert exported.output["count"] == 1
        assert "@" in exported.output["bibtex"]
    else:
        exported = bus.call("zotero", "export_bibtex", {"item_keys": []})
        assert exported.success
        assert exported.output["count"] == 0
        assert exported.output["bibtex"] == ""
