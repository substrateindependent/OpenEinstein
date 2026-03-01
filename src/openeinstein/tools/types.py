"""Typed tool bus models and interfaces."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """Tool metadata exposed by a server."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Normalized tool call result."""

    success: bool
    output: Any | None = None
    error: str | None = None
    retries: int = 0


class ToolServer(Protocol):
    """Protocol for in-process tool server adapters."""

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def health_check(self) -> bool: ...

    def list_tools(self) -> list[ToolSpec]: ...

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any: ...
