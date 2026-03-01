"""Integration tests for Cadabra MCP server."""

from __future__ import annotations

from pathlib import Path

from conftest import requires_cadabra
from openeinstein.tools import CadabraMCPServer, MCPConnectionManager, ToolBus


@requires_cadabra
def test_cadabra_server_live_expression_flow(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("cadabra", CadabraMCPServer(tmp_path / "cadabra"))
    bus = ToolBus(manager)

    tools = {spec.name for spec in bus.get_tools("cadabra")}
    assert {"create_session", "evaluate", "canonicalise", "recover_session"} <= tools

    created = bus.call("cadabra", "create_session", {"session_name": "default"})
    assert created.success
    session_id = created.output["session_id"]

    canonical = bus.call(
        "cadabra",
        "canonicalise",
        {"session_id": session_id, "expression": "A_{m} B^{m}", "timeout_seconds": 15},
    )
    assert canonical.success
    assert canonical.output["result"]

    # Force a failure by sending invalid syntax, then recover.
    failed = bus.call(
        "cadabra",
        "evaluate",
        {"session_id": session_id, "code": "this is invalid cadabra", "timeout_seconds": 5},
    )
    assert failed.success is False

    recovered = bus.call("cadabra", "recover_session", {"session_id": session_id})
    assert recovered.success
    assert recovered.output["recovered"] is True

    evaluated = bus.call(
        "cadabra",
        "evaluate",
        {
            "session_id": session_id,
            "code": "expr:=x_{m} y^{m};\nprint(expr)",
            "timeout_seconds": 15,
        },
    )
    assert evaluated.success
    assert "x" in evaluated.output["result"]
