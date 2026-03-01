# Tool Bus

## Purpose

ToolBus provides a transport-agnostic interface for MCP and CLI+JSON tools.

## Interfaces

- `ToolBus.get_tools(server_name) -> list[ToolSpec]`
- `ToolBus.call(server, tool, args, run_id=None) -> ToolResult`

## Invariants

- Agent and campaign code call tools only through ToolBus.
- Server crash handling retries at most 3 times.
- Tool schemas are validated at boundaries.
