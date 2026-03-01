# Integration Contract Ledger

This ledger tracks integration contracts per §17.5 of the implementation plan.

## Task 0.1: Initialize repository structure

- Files Created: repository scaffold files under `src/`, `tests/`, `configs/`, `docs/`, `campaign-packs/`, `campaigns/`.
- Files Modified: `scripts/setup-dev-environment.sh` updated to install into `.venv` for PEP 668-safe setup.
- Interfaces Exposed: initial package/module entry points and `openeinstein` CLI entrypoint.
- Database Changes: none.
- Config Changes: bootstrap `configs/openeinstein.example.yaml`, `configs/POLICY.json`.
- Depends On: none.
- Depended On By: all subsequent tasks.
- Verification Commands:
  - `.venv/bin/pip install -e .`
  - `.venv/bin/pytest -q`
- Consumption Proof:
  - Runtime path: `openeinstein` CLI loads from package entrypoint.
  - Integration test: bootstrap smoke tests in `tests/unit/test_smoke.py`.

## Task 0.2: Write CLAUDE.md, AGENTS.md, and CONTRIBUTING.md

- Files Created: none.
- Files Modified: `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md` (project guidance and guardrails).
- Interfaces Exposed: contributor/agent process contracts.
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 0.1.
- Depended On By: all implementation phases.
- Verification Commands:
  - `.venv/bin/pytest -q`
- Consumption Proof:
  - Runtime path: agent instructions consumed at kickoff.
  - Integration test: architecture guard checks enforced via subsequent tests and lint gates.

## Task 0.3: Write canonical documentation index and core architecture doc

- Files Created: none.
- Files Modified: `docs/canonical/_index.md`, `docs/canonical/core-architecture.md`.
- Interfaces Exposed: canonical architecture references.
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 0.2.
- Depended On By: phase pre-doc gates.
- Verification Commands:
  - `.venv/bin/pytest -q`
- Consumption Proof:
  - Runtime path: docs used in fresh-context validation before each phase.
  - Integration test: enforced by phase documentation gate process.

## Task 0.4: Write trust model document and PERSONALITY.md

- Files Created: none.
- Files Modified: `docs/trust-model.md`, `src/openeinstein/core/PERSONALITY.md`.
- Interfaces Exposed: operator boundary and canonical persona contract.
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 0.2.
- Depended On By: security, agent bootstrap, persona evals.
- Verification Commands:
  - `.venv/bin/pytest -q`
- Consumption Proof:
  - Runtime path: persona/trust constraints injected into agent bootstrap context.
  - Integration test: persona/security eval suites in later phases.

## Task 0.5: Write POLICY.json

- Files Created: `src/openeinstein/gateway/policy.py` (loader/validator), `tests/unit/test_policy_loading.py`.
- Files Modified: `configs/POLICY.json`, `src/openeinstein/gateway/__init__.py`.
- Interfaces Exposed: gateway policy loading and invariant validation API.
- Database Changes: none.
- Config Changes: policy schema validation contract.
- Depends On: Task 0.1.
- Depended On By: security subsystem and hooks.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_policy_loading.py -q`
- Consumption Proof:
  - Runtime path: gateway policy engine imports and validates `POLICY.json`.
  - Integration test: security tests use policy loader in tool call enforcement.

## Task 1.1: Implement model routing layer

- Files Created:
  - `src/openeinstein/routing/models.py`
  - `src/openeinstein/routing/router.py`
  - `tests/unit/test_routing.py`
  - `tests/integration/test_routing_integration.py`
  - `docs/canonical/model-routing.md`
- Files Modified:
  - `src/openeinstein/routing/__init__.py`
  - `docs/canonical/_index.md`
  - `docs/canonical/core-architecture.md`
  - `tests/integration/test_smoke_integration.py`
  - `docs/canonical/tool-bus.md`
  - `docs/canonical/tracing-and-evals.md`
  - `docs/canonical/gateway-control-plane.md`
- Interfaces Exposed:
  - `ModelRouter.resolve(role: ModelRole) -> ModelConfig`
  - `ModelRouter.resolve_with_fallback(role: ModelRole) -> list[ModelConfig]`
  - `ModelRouter.run_with_fallback(role: ModelRole, call: Callable[[ModelConfig], T]) -> T`
  - `load_routing_config(path) -> RoutingConfig`
- Database Changes: none.
- Config Changes: role-based routing config validation for `model_routing.roles`.
- Depends On: Task 0.1.
- Depended On By: agent base, orchestration, eval, and campaign execution tasks.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_routing.py -q`
  - `.venv/bin/pytest tests/integration/test_routing_integration.py -q`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: router is importable from `openeinstein.routing`.
  - Integration test: fallback path validated in `tests/integration/test_routing_integration.py`.

## Task 1.2: Implement tool bus (MCP + CLI+JSON)

- Files Created:
  - `src/openeinstein/tools/types.py`
  - `src/openeinstein/tools/tool_bus.py`
  - `tests/unit/test_tool_bus.py`
  - `tests/integration/test_tool_bus_mcp_roundtrip.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `ToolBus.get_tools(server_name: str) -> list[ToolSpec]`
  - `ToolBus.call(server: str, tool: str, args: dict[str, Any], run_id: str | None = None) -> ToolResult`
  - `MCPConnectionManager` lifecycle APIs
  - `CLIJSONToolWrapper.call(payload) -> dict[str, Any]`
- Database Changes: none.
- Config Changes: MCP server mapping loader from YAML (`mcp_servers`).
- Depends On: Task 1.1 (routing consumed by agents later).
- Depended On By: agents, campaign engine, security hooks.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_tool_bus.py -q`
  - `.venv/bin/pytest tests/integration/test_tool_bus_mcp_roundtrip.py -q`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: `ToolBus` exported via `openeinstein.tools`.
  - Integration test: server lifecycle + roundtrip in `tests/integration/test_tool_bus_mcp_roundtrip.py`.

## Task 1.3: Implement persistence layer

- Files Created:
  - `src/openeinstein/persistence/db.py`
  - `tests/unit/test_persistence.py`
- Files Modified:
  - `src/openeinstein/persistence/__init__.py`
- Interfaces Exposed:
  - `CampaignDB` typed CRUD methods for campaign state, candidates, failures, spans, evals, and approvals
  - migration API: `apply_migration(version, sql)`
- Database Changes:
  - Added schema for `campaign_state`, `candidates`, `failure_log`, `trace_spans`, `eval_results`, `approval_log`, and `schema_migrations`.
  - WAL mode enabled by default.
- Config Changes: none.
- Depends On: Task 0.1.
- Depended On By: tracing, eval framework, registry server, campaign engine, approvals and audit paths.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_persistence.py -q`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: persistence API importable via `openeinstein.persistence`.
  - Integration test consumer: registry MCP server tests (Task 1.7) consume these CRUD APIs.
