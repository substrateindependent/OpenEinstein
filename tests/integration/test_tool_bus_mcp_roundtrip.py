"""Integration roundtrip for in-process MCP-style server lifecycle."""

from __future__ import annotations

from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


def test_tool_bus_mcp_roundtrip_lifecycle() -> None:
    manager = MCPConnectionManager()
    server = InMemoryToolServer({"sum": lambda args: {"value": args["a"] + args["b"]}})
    manager.register_server("math", server)

    bus = ToolBus(manager)

    discovered = bus.get_tools("math")
    assert discovered and discovered[0].name == "sum"

    result = bus.call("math", "sum", {"a": 2, "b": 3})
    assert result.success
    assert result.output == {"value": 5}

    manager.stop_server("math")
    assert not manager.health_check("math")
