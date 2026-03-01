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

## Task 1.4: Implement tracing subsystem

- Files Created:
  - `src/openeinstein/tracing/core.py`
  - `tests/unit/test_tracing.py`
  - `tests/integration/test_tracing_cli_integration.py`
- Files Modified:
  - `src/openeinstein/tracing/__init__.py`
  - `src/openeinstein/persistence/db.py`
  - `src/openeinstein/persistence/__init__.py`
  - `src/openeinstein/cli/main.py`
- Interfaces Exposed:
  - `traced(span_name: str)` decorator
  - `TraceStore.record_span(...)`
  - `TraceStore.list_spans(run_id: str)`
  - `TraceStore.export_otlp_json(run_id: str)`
  - CLI: `openeinstein trace list` and `openeinstein trace export`
- Database Changes:
  - Reused existing `trace_spans` table with typed retrieval API `CampaignDB.get_trace_spans`.
- Config Changes: none.
- Depends On: Task 1.3.
- Depended On By: eval runner observability, control plane telemetry, campaign reporting.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_tracing.py -q`
  - `.venv/bin/pytest tests/integration/test_tracing_cli_integration.py -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: CLI subcommands use `TraceStore` against `.openeinstein/openeinstein.db`.
  - Integration test: `tests/integration/test_tracing_cli_integration.py` validates list/export roundtrip.

## Task 1.5: Implement eval framework scaffolding

- Files Created:
  - `src/openeinstein/evals/models.py`
  - `src/openeinstein/evals/runner.py`
  - `tests/unit/test_evals.py`
  - `tests/integration/test_eval_cli_integration.py`
- Files Modified:
  - `src/openeinstein/evals/__init__.py`
  - `src/openeinstein/cli/main.py`
  - `src/openeinstein/persistence/db.py`
  - `src/openeinstein/persistence/__init__.py`
  - `tests/unit/test_persistence.py`
- Interfaces Exposed:
  - `EvalRunner.load_suite(path) -> EvalSuite`
  - `EvalRunner.run_suite(suite, run_id?, executor?) -> EvalRunReport`
  - `discover_eval_suites(root) -> list[Path]`
  - `CampaignDB.get_eval_results(run_id: str | None = None)`
  - CLI: `openeinstein eval list|run|results`
- Database Changes:
  - No new table; added typed retrieval API for `eval_results`.
- Config Changes:
  - Eval suite YAML schema validated through `EvalSuiteDocument`.
- Depends On: Task 1.3 persistence and Task 1.4 tracing CLI structure.
- Depended On By: persona/skill/campaign eval tasks in later phases.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_evals.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_eval_cli_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: `openeinstein eval run` loads YAML suite, executes cases, and stores outcomes.
  - Integration test: `tests/integration/test_eval_cli_integration.py` validates list/run/results flow.

## Task 1.6: Implement control plane primitives

- Files Created:
  - `src/openeinstein/gateway/control_plane.py`
  - `tests/unit/test_control_plane.py`
  - `tests/integration/test_control_plane_cli_integration.py`
- Files Modified:
  - `src/openeinstein/gateway/__init__.py`
  - `src/openeinstein/cli/main.py`
- Interfaces Exposed:
  - `ControlPlane` protocol
  - `FileBackedControlPlane.issue_run_id/start_run/emit_event/get_events/get_status/stop_run/resume_run/wait_for_status/attach_artifact`
  - `RunEvent`, `RunRecord`, `ArtifactRecord`, `RunStatus`
  - CLI: `openeinstein run start|status|wait|events|stop|resume`
- Database Changes: none (JSON + JSONL file-backed state).
- Config Changes: none.
- Depends On: Task 0.5 policy boundary and phase 1 CLI scaffold.
- Depended On By: campaign engine lifecycle orchestration and report synthesis.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_control_plane.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_control_plane_cli_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: CLI run commands now resolve to `FileBackedControlPlane`.
  - Integration test: `tests/integration/test_control_plane_cli_integration.py` validates lifecycle operations and event stream output.

## Task 1.7: Implement Campaign Registry MCP server

- Files Created:
  - `src/openeinstein/tools/registry_server.py`
  - `tests/integration/test_registry_mcp.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `CampaignRegistryServer` implementing ToolServer lifecycle and tool dispatch
  - Tools: `add_candidate`, `update_gate_result`, `get_candidates`, `get_failure_log`, `get_statistics`
  - Pydantic JSON schema validation models for each tool payload
- Database Changes:
  - No schema change; consumed existing `CampaignDB` CRUD APIs.
- Config Changes: none.
- Depends On: Task 1.2 ToolBus and Task 1.3 persistence APIs.
- Depended On By: agent task orchestration, campaign engine persistence calls via ToolBus.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_registry_mcp.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: registry server is registered with `MCPConnectionManager` and invoked through `ToolBus`.
  - Integration test: `tests/integration/test_registry_mcp.py` validates discovery + roundtrip CRUD + validation failure.

## Task 2.1: Implement security subsystem

- Files Created:
  - `src/openeinstein/security/core.py`
  - `tests/unit/test_security.py`
  - `tests/integration/test_security_cli_integration.py`
- Files Modified:
  - `src/openeinstein/security/__init__.py`
  - `src/openeinstein/cli/main.py`
  - `docs/canonical/_index.md`
  - `docs/canonical/security-model.md`
  - `docs/canonical/multi-agent-orchestration.md`
  - `docs/canonical/personality.md`
- Interfaces Exposed:
  - `ApprovalsStore`, `PolicyEngine`, `PolicyEnforcementHook`, `SecureToolGateway`
  - `SecretRedactor`, `SecretsProvider`, `EnvFileSecretsProvider`, `KeyringSecretsProvider`
  - `SecurityScanner`, `ScanFinding`
  - `MetadataPinStore`, `ToolSandboxPolicy`
  - CLI: `openeinstein approvals list|grant|revoke|reset`, `openeinstein scan`
- Database Changes: none.
- Config Changes:
  - Enforces `configs/POLICY.json` invariants at runtime via `PolicyEngine`.
- Depends On: Task 0.5 policy loader and Task 1.2 ToolBus.
- Depended On By: hook system (Task 2.2), all guarded tool-call paths, later security audit tasks.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_security.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_security_cli_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: approvals and scan are exercised by CLI commands.
  - Integration test: `tests/integration/test_security_cli_integration.py` validates approvals workflow and scan detection.
