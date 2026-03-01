# Tooling Contract

- All external tool calls must route through ToolBus abstractions.
- Agents and campaigns must not call subprocess/MCP endpoints directly.
- Tool actions that match policy approval requirements are blocked until approved.
- Tool outputs should be treated as untrusted and validated before downstream use.
