"""Integration tests for Python sandbox MCP server."""

from __future__ import annotations

from openeinstein.tools import MCPConnectionManager, PythonSandboxMCPServer, ToolBus


def test_python_sandbox_execution_and_policy_enforcement(tmp_path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("sandbox", PythonSandboxMCPServer(tmp_path / "sandbox"))
    bus = ToolBus(manager)

    executed = bus.call(
        "sandbox",
        "execute",
        {"code": "result = 2 + 2\nprint('ok')"},
    )
    assert executed.success
    assert executed.output["result"] == 4
    assert "ok" in executed.output["stdout"]

    blocked = bus.call("sandbox", "execute", {"code": "import socket\nresult = 1"})
    assert blocked.success is False
    assert "Forbidden import" in (blocked.error or "")

    integrated = bus.call(
        "sandbox",
        "integrate",
        {"expression": "x**2", "x_min": 0.0, "x_max": 1.0},
    )
    assert integrated.success
    assert abs(integrated.output["value"] - (1.0 / 3.0)) < 1e-3
