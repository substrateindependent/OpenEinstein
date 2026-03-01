"""Integration tests for SymPy MCP server."""

from __future__ import annotations

from pathlib import Path

from openeinstein.tools import MCPConnectionManager, SympyMCPServer, ToolBus


def test_sympy_server_sessions_and_capabilities(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("sympy", SympyMCPServer(tmp_path / "sympy"))
    bus = ToolBus(manager)

    tools = {spec.name for spec in bus.get_tools("sympy")}
    assert {"create_session", "evaluate", "simplify", "close_session", "capabilities"} <= tools

    created = bus.call("sympy", "create_session", {"session_name": "default"})
    assert created.success
    session_id = created.output["session_id"]

    evaluated = bus.call(
        "sympy",
        "evaluate",
        {"session_id": session_id, "expression": "x + x"},
    )
    assert evaluated.success
    assert "2*x" in evaluated.output["result"]

    simplified = bus.call(
        "sympy",
        "simplify",
        {"session_id": session_id, "expression": "sin(x)**2 + cos(x)**2"},
    )
    assert simplified.success
    assert simplified.output["result"] == "1"

    capabilities = bus.call("sympy", "capabilities", {})
    assert capabilities.success
    assert "symbolic_simplify" in capabilities.output["capabilities"]

    closed = bus.call("sympy", "close_session", {"session_id": session_id})
    assert closed.success
