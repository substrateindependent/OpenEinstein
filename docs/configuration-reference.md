# Configuration Reference

This document describes the runtime configuration contract for OpenEinstein.

## Main Config File

Default example: `configs/openeinstein.example.yaml`

Top-level keys:

1. `model_routing`
2. `hooks`
3. `mcp_servers`

## `model_routing`

Defines logical role routing. Do not hardcode provider/model names in feature logic.

```yaml
model_routing:
  roles:
    reasoning:
      description: Complex reasoning
      default:
        provider: anthropic
        model: claude-opus-4-6
        params: {}
      fallback:
        provider: openai
        model: o3
```

Required roles:

1. `reasoning`
2. `generation`
3. `fast`
4. `embeddings`

Each role supports:

1. `description: str`
2. `default: {provider, model, params?}`
3. `fallback: {provider, model, params?} | list[...]` (optional)

## `hooks`

Declares hook handlers for gateway events. Built-in hook loading uses YAML in the format:

```yaml
hooks:
  before_tool_call:
    - type: approval_gate
  after_tool_call:
    - type: audit
      path: .openeinstein/hooks-audit.jsonl
```

The repository example also includes architecture intent metadata for hook handlers.

## `mcp_servers`

Declares MCP/adapter server launch contract used by tool infrastructure.

Example:

```yaml
mcp_servers:
  sympy:
    type: stdio
    command: openeinstein-mcp-sympy
    required: true
    sandbox:
      network: none
      workspace_access: rw
```

Fields:

1. `type`: adapter transport type (typically `stdio`)
2. `command`: executable or wrapper command
3. `args`: optional command arguments
4. `required`: whether startup is mandatory
5. `sandbox`: tool-specific sandbox envelope

## Policy File

Machine-enforced invariants are defined in `configs/POLICY.json`.

Required shape:

1. `version`
2. `invariants.require_approval_for`
3. `invariants.max_llm_calls_per_step`
4. `invariants.max_cas_timeout_minutes`
5. `invariants.forbidden_operations`
6. `invariants.require_verification_after_gates`
7. `enforced_by` (`gateway`)
8. `note`

Validate via:

```bash
openeinstein config --validate --path configs/openeinstein.example.yaml
```
