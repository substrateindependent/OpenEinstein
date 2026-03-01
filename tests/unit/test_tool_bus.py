"""Unit tests for ToolBus behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.tools import (
    CLIJSONToolWrapper,
    InMemoryToolServer,
    MCPConnectionManager,
    ToolBus,
    ToolBusError,
    ToolServerCrash,
    load_tool_servers_from_yaml,
)


def test_tool_bus_discovers_and_calls_tool() -> None:
    manager = MCPConnectionManager()
    server = InMemoryToolServer({"echo": lambda args: {"echo": args["message"]}})
    manager.register_server("test", server)

    bus = ToolBus(manager)
    tools = bus.get_tools("test")
    assert any(tool.name == "echo" for tool in tools)

    result = bus.call("test", "echo", {"message": "hi"})
    assert result.success
    assert result.output == {"echo": "hi"}


def test_tool_bus_retries_on_crash() -> None:
    class CrashyServer(InMemoryToolServer):
        def __init__(self) -> None:
            super().__init__({"ok": lambda _args: {"ok": True}})
            self.calls = 0

        def call_tool(self, tool_name: str, args: dict[str, object]) -> object:
            self.calls += 1
            if self.calls < 3:
                raise ToolServerCrash("boom")
            return super().call_tool(tool_name, args)

    manager = MCPConnectionManager()
    manager.register_server("crashy", CrashyServer())
    bus = ToolBus(manager, max_retries=3)

    result = bus.call("crashy", "ok", {})
    assert result.success
    assert result.retries == 2


def test_load_tool_servers_from_yaml() -> None:
    servers = load_tool_servers_from_yaml(Path("configs/openeinstein.example.yaml"))
    assert "sympy" in servers


def test_cli_json_wrapper_parses_output() -> None:
    wrapper = CLIJSONToolWrapper(["/bin/sh", "-lc", "cat"])
    output = wrapper.call({"x": 1})
    assert output["x"] == 1


def test_cli_json_wrapper_errors_on_bad_json() -> None:
    wrapper = CLIJSONToolWrapper(["/bin/sh", "-lc", "echo not-json"])
    with pytest.raises(ToolBusError):
        wrapper.call({"x": 1})
