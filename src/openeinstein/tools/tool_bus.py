"""Unified ToolBus with MCP-like and CLI+JSON adapters."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

import yaml  # type: ignore[import-untyped]

from openeinstein.tools.types import ToolResult, ToolServer, ToolSpec


class ToolBusError(RuntimeError):
    """Base tool bus error."""


class ToolServerCrash(ToolBusError):
    """Raised when a tool server crashes during call."""


class CLIJSONToolWrapper:
    """Thin wrapper for fire-and-forget CLI+JSON tools."""

    def __init__(self, command: list[str]) -> None:
        self.command = command

    def call(self, payload: dict[str, Any]) -> dict[str, Any]:
        completed = subprocess.run(
            self.command,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ToolBusError(completed.stderr.strip() or "CLI tool failed")
        try:
            return json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise ToolBusError("CLI tool did not return valid JSON") from exc


class InMemoryToolServer:
    """Simple in-process server used for tests and local wiring."""

    def __init__(self, tools: dict[str, Callable[[dict[str, Any]], Any]]) -> None:
        self._tool_funcs = tools
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name=name, description=f"In-memory tool: {name}")
            for name in self._tool_funcs
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("Server not started")
        if tool_name not in self._tool_funcs:
            raise ToolBusError(f"Tool not found: {tool_name}")
        return self._tool_funcs[tool_name](args)


class MCPConnectionManager:
    """Lifecycle manager for registered tool servers."""

    def __init__(self) -> None:
        self._servers: dict[str, ToolServer] = {}

    def register_server(self, name: str, server: ToolServer) -> None:
        self._servers[name] = server

    def start_server(self, name: str) -> None:
        self._servers[name].start()

    def stop_server(self, name: str) -> None:
        self._servers[name].stop()

    def health_check(self, name: str) -> bool:
        return self._servers[name].health_check()

    def get_server(self, name: str) -> ToolServer:
        if name not in self._servers:
            raise ToolBusError(f"Unknown server: {name}")
        return self._servers[name]

    def list_server_names(self) -> list[str]:
        return sorted(self._servers)


class ToolBus:
    """Transport-agnostic tool caller with retry-on-crash semantics."""

    def __init__(self, manager: MCPConnectionManager, max_retries: int = 3) -> None:
        self._manager = manager
        self._max_retries = max_retries

    def get_tools(self, server_name: str) -> list[ToolSpec]:
        server = self._manager.get_server(server_name)
        if not self._manager.health_check(server_name):
            self._manager.start_server(server_name)
        return server.list_tools()

    def call(
        self,
        server: str,
        tool: str,
        args: dict[str, Any],
        run_id: str | None = None,
    ) -> ToolResult:
        server_obj = self._manager.get_server(server)
        retries = 0
        for attempt in range(self._max_retries + 1):
            try:
                if not self._manager.health_check(server):
                    self._manager.start_server(server)
                output = server_obj.call_tool(tool, args)
                if run_id is not None and isinstance(output, dict):
                    output.setdefault("run_id", run_id)
                return ToolResult(success=True, output=output, retries=retries)
            except ToolServerCrash:
                retries += 1
                self._manager.stop_server(server)
                if attempt >= self._max_retries:
                    return ToolResult(success=False, error="server crashed", retries=retries)
                self._manager.start_server(server)
            except Exception as exc:
                return ToolResult(success=False, error=str(exc), retries=retries)
        return ToolResult(success=False, error="tool call failed", retries=retries)


def load_tool_servers_from_yaml(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load MCP server definitions from YAML config."""

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    servers = payload.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ToolBusError("mcp_servers must be a mapping")
    return servers
