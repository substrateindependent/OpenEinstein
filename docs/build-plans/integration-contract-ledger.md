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

## Task 2.2: Implement hook system

- Files Created:
  - `src/openeinstein/gateway/hooks.py`
  - `tests/unit/test_hooks.py`
  - `tests/integration/test_hooks_integration.py`
- Files Modified:
  - `src/openeinstein/gateway/__init__.py`
  - `src/openeinstein/security/core.py`
- Interfaces Exposed:
  - `HookRegistry.register/dispatch`
  - `HookContext`, `HookResponse`, `HookDispatchResult`, `HookPoint`
  - Built-ins: `AuditLoggerHook`, `ApprovalGateHook`
  - Loader: `register_hooks_from_yaml(...)`
  - Runtime consumer: `HookedToolGateway.call_tool(...)`
- Database Changes: none.
- Config Changes:
  - YAML hook registration contract (`hooks` map with built-in `audit` and `approval_gate` types).
- Depends On: Task 2.1 policy and approvals primitives.
- Depended On By: agent orchestration and campaign state transition instrumentation.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_hooks.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_hooks_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: `HookedToolGateway` invokes before/after hook points around ToolBus calls.
  - Integration test: `tests/integration/test_hooks_integration.py` validates approval blocking and audit hook logging.

## Task 2.3: Implement skill registry and base agent abstractions

- Files Created:
  - `src/openeinstein/skills/models.py`
  - `src/openeinstein/skills/registry.py`
  - `src/openeinstein/agents/base.py`
  - `src/openeinstein/core/TOOLS.md`
  - `tests/unit/test_skills.py`
  - `tests/unit/test_agent_base.py`
  - `tests/integration/test_context_report_cli_integration.py`
- Files Modified:
  - `src/openeinstein/skills/__init__.py`
  - `src/openeinstein/agents/__init__.py`
  - `src/openeinstein/cli/main.py`
- Interfaces Exposed:
  - Skill models: `SkillMetadata`, `SkillInstructions`, `SkillResources`, `SkillContextBundle`, `ContextReport`
  - `SkillRegistry.discover_skills/load_instructions/build_context`
  - Agent base: `OpenEinsteinAgent`, `AgentBootstrapContext`
  - CLI: `openeinstein context report`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 1.1 routing, Task 1.2 ToolBus, Task 0.5 policy config.
- Depended On By: orchestrator and specialized agent implementations (Tasks 2.4-2.7).
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_skills.py tests/unit/test_agent_base.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_context_report_cli_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: `OpenEinsteinAgent.build_bootstrap_context` injects persona/tools/policy and bounded skill context.
  - Integration test: `tests/integration/test_context_report_cli_integration.py` validates context reporting through CLI.

## Task 2.4: Implement orchestrator with delegation and compaction

- Files Created:
  - `src/openeinstein/agents/orchestrator.py`
  - `tests/unit/test_orchestrator.py`
  - `tests/integration/test_orchestrator_integration.py`
- Files Modified:
  - `src/openeinstein/agents/__init__.py`
- Interfaces Exposed:
  - `AgentOrchestrator.execute(...)`
  - `AgentOrchestrator.compact_with_invariants(...)`
  - Models: `DelegatedTask`, `TaskResult`, `OrchestrationSummary`
  - Scheduler protocol: `AdaptiveScheduler`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 2.3 base agent abstraction.
- Depended On By: specialized computation/literature/verification agents and campaign execution pipeline.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_orchestrator.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_orchestrator_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: orchestrator executes bound subagents and returns aggregated output.
  - Integration test: `tests/integration/test_orchestrator_integration.py` validates execution flow and failure handling.

## Task 2.5: Implement computation agent

- Files Created:
  - `src/openeinstein/agents/computation.py`
  - `tests/unit/test_computation_agent.py`
  - `tests/integration/test_computation_agent_integration.py`
- Files Modified:
  - `src/openeinstein/agents/__init__.py`
- Interfaces Exposed:
  - `ComputationAgent.run(...)` with template fill, timeout, fallback, and gate sequence execution
  - `ComputationAgent.render_template(...)`
  - Models: `GateResult`, `ComputationRunResult`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 2.3 base agent and Task 1.2 ToolBus.
- Depended On By: campaign gate execution and CAS-backed scoring flows.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_computation_agent.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_computation_agent_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: computation agent invokes CAS through ToolBus and applies gate sequence.
  - Integration test: `tests/integration/test_computation_agent_integration.py` validates gate failure path end-to-end.

## Task 2.6: Implement literature agent

- Files Created:
  - `src/openeinstein/agents/literature.py`
  - `tests/unit/test_literature_agent.py`
  - `tests/integration/test_literature_agent_integration.py`
- Files Modified:
  - `src/openeinstein/agents/__init__.py`
- Interfaces Exposed:
  - `LiteratureAgent.run(...)` for multi-source query, dedup, deterministic ranking, and BibTeX rendering
  - Models: `LiteratureCandidate`, `LiteratureRunResult`
  - Source protocol: `LiteratureSource`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 2.3 base agent abstraction.
- Depended On By: campaign literature workflows and report synthesis.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_literature_agent.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_literature_agent_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: literature agent merges and ranks source outputs and generates BibTeX.
  - Integration test: `tests/integration/test_literature_agent_integration.py` validates cache hook lifecycle and output schema.

## Task 2.7: Implement verification agent

- Files Created:
  - `src/openeinstein/agents/verification.py`
  - `tests/unit/test_verification_agent.py`
  - `tests/integration/test_verification_agent_integration.py`
- Files Modified:
  - `src/openeinstein/agents/__init__.py`
- Interfaces Exposed:
  - `VerificationAgent.run(...)`
  - `VerificationAgent.detect_inconsistencies(...)`
  - Models: `VerificationIssue`, `VerificationReport`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 2.3 base agent abstraction.
- Depended On By: campaign review/triage and security audit checks in later phases.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_verification_agent.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_verification_agent_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: verification agent ingests claim sets and returns structured review flags.
  - Integration test: `tests/integration/test_verification_agent_integration.py` validates no-inconsistency path.

## Task 3.1: Implement SymPy MCP server

- Files Created:
  - `src/openeinstein/tools/sympy_server.py`
  - `tests/integration/test_sympy_mcp.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `SympyMCPServer` with tools: `create_session`, `evaluate`, `simplify`, `close_session`, `capabilities`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 1.2 ToolBus server lifecycle contract.
- Depended On By: computation agent CAS routing and template backend mapping tasks.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_sympy_mcp.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: SymPy server is registered in `MCPConnectionManager` and invoked through `ToolBus`.
  - Integration test: `tests/integration/test_sympy_mcp.py` validates session lifecycle and capabilities.

## Task 3.2: Implement Mathematica MCP server

- Files Created:
  - `src/openeinstein/tools/mathematica_server.py`
  - `tests/integration/test_mathematica_mcp.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `MathematicaMCPServer` with tools: `create_session`, `evaluate`, `load_xact`, `recover_kernel`, `close_session`, `capabilities`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 1.2 ToolBus and wolframscript availability.
- Depended On By: tensor/CAS backend routing and computation template execution.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_mathematica_mcp.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: Mathematica server executes through ToolBus with journaling and recovery hooks.
  - Integration test: `tests/integration/test_mathematica_mcp.py` validates evaluate/xAct/timeout/recovery lifecycle.

## Task 3.3: Implement Cadabra MCP server

- Files Created:
  - `src/openeinstein/tools/cadabra_server.py`
  - `tests/integration/test_cadabra_mcp.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
  - `tests/conftest.py`
  - `BUILD-READY.md` (contract reconciliation)
  - `pyproject.toml` (packaging reconciliation)
  - `OpenEinstein-Implementation-Plan.md` (appendix reconciliation)
- Interfaces Exposed:
  - `CadabraMCPServer` with tools: `create_session`, `evaluate`, `canonicalise`, `recover_session`, `close_session`, `capabilities`
- Database Changes: none.
- Config Changes:
  - Updated cadabra skip marker to allow CLI-runtime detection (`cadabra2` binary) in addition to Python module lookup.
  - Reconciled dependency contract to treat Cadabra as a system CLI runtime (`cadabra2` in `PATH`) instead of a PyPI package.
  - Updated optional extra `cadabra` to an empty marker extra so editable install remains valid.
- Depends On: Task 1.2 ToolBus contract and local `cadabra2` runtime.
- Depended On By: capability-first CAS routing and computation backend selection.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_cadabra_mcp.py --tb=short -q`
  - `.venv/bin/pip install -e ".[dev]"`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: Cadabra server executes tensor operations through ToolBus using live `cadabra2` CLI.
  - Integration test: `tests/integration/test_cadabra_mcp.py` validates expression execution and recovery flow.

## Task 3.4: Implement template registry and backend mapping

- Files Created:
  - `src/openeinstein/campaigns/templates.py`
  - `tests/unit/test_templates.py`
  - `tests/integration/test_template_registry_integration.py`
- Files Modified:
  - `src/openeinstein/campaigns/__init__.py`
  - `src/openeinstein/agents/computation.py`
- Interfaces Exposed:
  - `TemplateRegistry.register/load_directory/get/render/available_backends/validate_syntax`
  - Models: `BackendTemplate`, `ComputeTemplate`, `TemplateDocument`
- Database Changes: none.
- Config Changes:
  - Template documents support versioned backend-specific bodies with `{{var}}` placeholders.
- Depends On: Task 2.5 computation agent and CAS backend tasks.
- Depended On By: gate pipeline execution and multi-backend template routing.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_templates.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_template_registry_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: `ComputationAgent` resolves `template_id` through `TemplateRegistry` and rerenders for fallback backends.
  - Integration test: `tests/integration/test_template_registry_integration.py` validates backend-specific fallback rendering.

## Task 3.5: Implement scanner MCP server

- Files Created:
  - `src/openeinstein/tools/scanner_server.py`
  - `tests/integration/test_scanner_mcp.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `ScannerMCPServer` with tools: `scan_grid`, `scan_adaptive`, `find_boundary`, `capabilities`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 1.2 ToolBus lifecycle and numerical dependencies (`numpy`, `matplotlib`).
- Depended On By: adaptive sampling and campaign boundary-search workflows.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_scanner_mcp.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: scanner server executes numerical scans via ToolBus and emits plot artifacts.
  - Integration test: `tests/integration/test_scanner_mcp.py` validates known-function viability region and boundary detection.

## Task 3.6: Implement sandboxed Python MCP server

- Files Created:
  - `src/openeinstein/tools/python_sandbox_server.py`
  - `tests/integration/test_python_sandbox.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `PythonSandboxMCPServer` with tools: `execute`, `integrate`, `minimize`, `capabilities`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 1.2 ToolBus contract and scientific dependencies (`numpy`, `scipy`).
- Depended On By: numerical evaluation paths and safety-audit flows.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_python_sandbox.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: sandbox server executes restricted code and numerical helpers via ToolBus.
  - Integration test: `tests/integration/test_python_sandbox.py` validates execution output and forbidden-import blocking.

## Task 4.1: Integrate arXiv MCP server

- Files Created:
  - `src/openeinstein/tools/arxiv_server.py`
  - `tests/unit/test_arxiv_server.py`
  - `tests/integration/test_arxiv_mcp.py`
  - `docs/canonical/literature-infrastructure.md` (phase pre-doc gate)
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
  - `docs/canonical/_index.md`
- Interfaces Exposed:
  - `ArxivMCPServer` with tools: `search`, `download_pdf`, `capabilities`
  - Pydantic models: `ArxivSearchArgs`, `ArxivDownloadArgs`
- Database Changes: none.
- Config Changes:
  - Added canonical literature infrastructure document and index entry for Phase 4 pre-doc gate.
- Depends On: Task 1.2 ToolBus contract and network connectivity.
- Depended On By: literature agent source adapters, bibliography generation, campaign literature seeding.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_arxiv_server.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_arxiv_mcp.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: arXiv tool server is registered in `MCPConnectionManager` and invoked through `ToolBus`.
  - Integration test: `tests/integration/test_arxiv_mcp.py` validates live search + PDF download.

## Task 4.2: Integrate Semantic Scholar MCP

- Files Created:
  - `src/openeinstein/tools/semantic_scholar_server.py`
  - `tests/unit/test_semantic_scholar_server.py`
  - `tests/integration/test_semantic_scholar_mcp.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `SemanticScholarMCPServer` with tools: `search`, `get_paper`, `capabilities`
  - Pydantic models: `SemanticScholarSearchArgs`, `SemanticScholarPaperArgs`
- Database Changes: none.
- Config Changes:
  - Semantic Scholar integration supports API-key headers (`S2_API_KEY`) and keyless fallback behavior.
- Depends On: Task 1.2 ToolBus contract and network connectivity.
- Depended On By: literature-agent multi-source aggregation and citation-metric enrichment.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_semantic_scholar_server.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_semantic_scholar_mcp.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: Semantic Scholar tool server is registered in `MCPConnectionManager` and invoked via `ToolBus`.
  - Integration test: `tests/integration/test_semantic_scholar_mcp.py` validates live search and paper lookup with keyless probe fallback.

## Task 4.3: Implement INSPIRE-HEP connector

- Files Created:
  - `src/openeinstein/tools/inspire_server.py`
  - `tests/unit/test_inspire_server.py`
  - `tests/integration/test_inspire_connector.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `InspireMCPServer` with tools: `search_literature`, `lookup_author`, `export_citations`, `capabilities`
  - Pydantic models: `InspireSearchArgs`, `InspireCitationArgs`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 1.2 ToolBus contract and network connectivity.
- Depended On By: literature-agent source fusion and citation-chain enrichment.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_inspire_server.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_inspire_connector.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: INSPIRE connector server is registered in `MCPConnectionManager` and invoked via `ToolBus`.
  - Integration test: `tests/integration/test_inspire_connector.py` validates live literature search, author lookup, and citation export.

## Task 4.4: Implement NASA ADS connector

- Files Created:
  - `src/openeinstein/tools/ads_server.py`
  - `tests/unit/test_ads_server.py`
  - `tests/integration/test_ads_connector.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
  - `tests/conftest.py` (load `.env` before key-dependent skip marker evaluation)
- Interfaces Exposed:
  - `ADSMCPServer` with tools: `search`, `citation_metrics`, `capabilities`
  - Pydantic models: `ADSSearchArgs`, `ADSMetricsArgs`
- Database Changes: none.
- Config Changes:
  - API-key tests now resolve credentials from repository `.env` (without overriding process env).
- Depends On: Task 1.2 ToolBus contract, network connectivity, `ADS_API_KEY`.
- Depended On By: literature-agent citation metrics and ranking features.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_ads_server.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_ads_connector.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: ADS connector server is registered in `MCPConnectionManager` and invoked via `ToolBus`.
  - Integration test: `tests/integration/test_ads_connector.py` validates live search and citation metrics lookup.

## Task 4.5: Integrate CrossRef MCP

- Files Created:
  - `src/openeinstein/tools/crossref_server.py`
  - `tests/unit/test_crossref_server.py`
  - `tests/integration/test_crossref_mcp.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `CrossrefMCPServer` with tools: `resolve_doi`, `search_works`, `capabilities`
  - Pydantic models: `CrossrefDOIArgs`, `CrossrefSearchArgs`
- Database Changes: none.
- Config Changes:
  - Uses optional `CROSSREF_MAILTO` for polite-pool API requests.
- Depends On: Task 1.2 ToolBus contract and network connectivity.
- Depended On By: DOI normalization and citation metadata enrichment in literature workflows.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_crossref_server.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_crossref_mcp.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: CrossRef connector server is registered in `MCPConnectionManager` and invoked via `ToolBus`.
  - Integration test: `tests/integration/test_crossref_mcp.py` validates DOI resolution and search roundtrip.

## Task 4.6: Implement Zotero integration

- Files Created:
  - `src/openeinstein/tools/zotero_server.py`
  - `tests/unit/test_zotero_server.py`
  - `tests/integration/test_zotero_connector.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `ZoteroMCPServer` with tools: `sync_library`, `export_bibtex`, `capabilities`
  - Pydantic models: `ZoteroSyncArgs`, `ZoteroBibtexArgs`
- Database Changes: none.
- Config Changes:
  - Connector reads `ZOTERO_API_KEY` and `ZOTERO_USER_ID` from environment.
- Depends On: Task 1.2 ToolBus contract, network connectivity, Zotero credentials.
- Depended On By: bibliography sync/export workflows and literature-source fusion.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_zotero_server.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_zotero_connector.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: Zotero connector server is registered in `MCPConnectionManager` and invoked via `ToolBus`.
  - Integration test: `tests/integration/test_zotero_connector.py` validates live sync and BibTeX export behavior.

## Task 4.7: Implement GROBID PDF ingestion

- Files Created:
  - `src/openeinstein/tools/grobid_server.py`
  - `tests/unit/test_grobid_server.py`
  - `tests/integration/test_grobid_ingestion.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
- Interfaces Exposed:
  - `GrobidMCPServer` with tools: `start_service`, `stop_service`, `ingest_pdf`, `capabilities`
  - Pydantic models: `StartServiceArgs`, `IngestPDFArgs`, `StopServiceArgs`
- Database Changes: none.
- Config Changes:
  - Docker-backed service lifecycle for GROBID container (`lfoppiano/grobid:0.8.0`).
- Depends On: Task 1.2 ToolBus contract, Docker daemon, network access.
- Depended On By: literature ingestion pipeline and reference extraction in report synthesis.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_grobid_server.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_grobid_ingestion.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: GROBID wrapper server is registered in `MCPConnectionManager` and invoked via `ToolBus`.
  - Integration test: `tests/integration/test_grobid_ingestion.py` validates live Docker service startup and PDF ingestion.

## Task 4.8: Implement LaTeX publishing toolchain

- Files Created:
  - `src/openeinstein/tools/latex_toolchain.py`
  - `tests/unit/test_latex_toolchain.py`
  - `tests/integration/test_latex_toolchain.py`
- Files Modified:
  - `src/openeinstein/tools/__init__.py`
  - `src/openeinstein/cli/main.py`
- Interfaces Exposed:
  - `LatexToolchain.compile`, `LatexToolchain.clean`, `LatexToolchain.generate_bibtex`, `LatexToolchain.generate_skeleton`
  - Models: `BibEntry`, `CompileResult`
  - CLI: `openeinstein latex skeleton|compile|clean|bibgen`
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 1.2 ToolBus conventions, LaTeX system dependency (`latexmk`).
- Depended On By: report synthesis and publication/export workflows.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_latex_toolchain.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_latex_toolchain.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: LaTeX wrappers are consumed directly by CLI commands under `openeinstein latex`.
  - Integration test: `tests/integration/test_latex_toolchain.py` validates compile/clean workflow and CLI command behavior.

## Task 5.1: Implement campaign config loader

- Files Created:
  - `src/openeinstein/campaigns/config.py`
  - `tests/unit/test_campaign_config.py`
  - `tests/integration/test_campaign_config_integration.py`
- Files Modified:
  - `src/openeinstein/campaigns/__init__.py`
- Interfaces Exposed:
  - `CampaignConfigLoader.discover_packs/load_pack/load_config/resolve_capabilities/validate_runtime_requirements`
  - Models: `CampaignDefinition`, `GateConfig`, `CampaignDependencies`, `LoadedCampaignPack`
- Database Changes: none.
- Config Changes:
  - Campaign YAML now validated through strict Pydantic envelope model.
- Depends On: existing campaign pack structure and Task 1.2 capability-first tool boundaries.
- Depended On By: campaign state machine and gate pipeline runner.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_campaign_config.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_campaign_config_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: campaign packs are discovered and loaded through `CampaignConfigLoader`.
  - Integration test: `tests/integration/test_campaign_config_integration.py` validates pack discovery + runtime capability/dependency validation.

## Task 5.2: Implement campaign state machine

- Files Created:
  - `src/openeinstein/campaigns/state.py`
  - `tests/unit/test_campaign_state.py`
  - `tests/integration/test_campaign_state_integration.py`
- Files Modified:
  - `src/openeinstein/campaigns/__init__.py`
- Interfaces Exposed:
  - `CampaignStateMachine.initialize_run/transition/checkpoint/resume/record_candidate`
  - Models: `CampaignSnapshot`, `CandidateRecordResult`
- Database Changes:
  - Consumes existing `campaign_state` and `candidates` tables for checkpoint and idempotency tracking.
- Config Changes: none.
- Depends On: Task 1.3 persistence and Task 1.6 control-plane event streams.
- Depended On By: gate pipeline runner and adaptive sampling orchestration.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_campaign_state.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_campaign_state_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: campaign lifecycle transitions are persisted and emitted through `CampaignStateMachine`.
  - Integration test: `tests/integration/test_campaign_state_integration.py` validates crash-close, restart, resume, and completion flow.

## Task 5.3: Implement gate pipeline runner

- Files Created:
  - `src/openeinstein/campaigns/pipeline.py`
  - `tests/unit/test_gate_pipeline.py`
  - `tests/integration/test_gate_pipeline_integration.py`
- Files Modified:
  - `src/openeinstein/campaigns/__init__.py`
- Interfaces Exposed:
  - `GatePipelineRunner.select_backend/run_candidate/run_batch`
  - Models: `GateExecutionResult`, `CandidateInput`
- Database Changes:
  - Uses `candidates` and `failure_log` tables for gate result persistence and failure classification.
- Config Changes: none.
- Depends On: Task 5.1 `GateConfig`, Task 1.3 persistence contract.
- Depended On By: adaptive sampling engine and campaign execution loops.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_gate_pipeline.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_gate_pipeline_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: candidates execute sequential gate flows through `GatePipelineRunner` with capability-based backend routing.
  - Integration test: `tests/integration/test_gate_pipeline_integration.py` validates batch execution routing and persistence side effects.

## Task 5.4: Implement adaptive sampling engine

- Files Created:
  - `src/openeinstein/campaigns/sampling.py`
  - `tests/unit/test_adaptive_sampling.py`
  - `tests/integration/test_adaptive_sampling_integration.py`
- Files Modified:
  - `src/openeinstein/campaigns/__init__.py`
- Interfaces Exposed:
  - `AdaptiveSampler.reprioritize/reprioritize_keys`
  - Models: `SamplingCandidate`, `SamplingDecision`
- Database Changes:
  - Consumes `failure_log` records as sampling signal input.
- Config Changes: none.
- Depends On: Task 5.2/5.3 failure persistence and candidate metadata contracts.
- Depended On By: campaign execution loop scheduling and future dynamic queue management.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_adaptive_sampling.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_adaptive_sampling_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: adaptive sampler reprioritizes candidate keys from persisted failure patterns.
  - Integration test: `tests/integration/test_adaptive_sampling_integration.py` validates deterministic ordering using DB failure logs.

## Task 6.1: Implement CLI

- Files Created:
  - `tests/integration/test_cli_commands.py`
- Files Modified:
  - `src/openeinstein/cli/main.py`
- Interfaces Exposed:
  - New CLI surfaces: `init`, `results`, `export`, `config`, `sandbox explain`, `pack list`, `campaign clean`
  - Extended CLI surfaces: `pack install` local install path, `latex build` alias
- Database Changes: none.
- Config Changes:
  - `config --validate` enforces presence of required top-level config keys.
- Depends On: Tasks 1.x control plane/evals/tracing/security and Task 5 campaign primitives.
- Depended On By: report generation commands and phase-7 operator workflows.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_cli_commands.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: users can initialize workspace, inspect runs, export results, diagnose sandbox blocks, and clean campaign data via CLI.
  - Integration test: `tests/integration/test_cli_commands.py` validates help output and functional command roundtrips.

## Task 6.2: Implement report generation

- Files Created:
  - `src/openeinstein/reports/__init__.py`
  - `src/openeinstein/reports/generator.py`
  - `tests/unit/test_report_generation.py`
  - `tests/integration/test_report_generation_integration.py`
- Files Modified:
  - `src/openeinstein/cli/main.py`
  - `tests/conftest.py`
  - `tests/integration/test_mathematica_mcp.py`
- Interfaces Exposed:
  - `CampaignReportGenerator.synthesize/to_markdown/write_markdown/export_latex`
  - Models: `CampaignReport`, `ReportCandidate`
  - CLI: `openeinstein report generate`
- Database Changes:
  - Consumes candidate/failure records from persistence for report synthesis.
- Config Changes:
  - None.
- Depends On: Task 1.3 persistence, Task 6.1 CLI plumbing.
- Depended On By: final campaign-pack validation and operator reporting workflows.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_report_generation.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_report_generation_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: CLI `report generate` synthesizes markdown/latex reports from persisted campaign data.
  - Integration test: `tests/integration/test_report_generation_integration.py` validates markdown and LaTeX output generation.

## Task 7.1: Write the first Campaign Pack

- Files Created:
  - `campaign-packs/modified-gravity-action-search/templates/cosmology-reduction.yaml`
  - `campaign-packs/modified-gravity-action-search/templates/perturbation-analysis.yaml`
  - `campaign-packs/modified-gravity-action-search/templates/stability-analysis.yaml`
  - `tests/unit/test_modified_gravity_pack.py`
  - `tests/integration/test_modified_gravity_pack.py`
- Files Modified:
  - `campaign-packs/modified-gravity-action-search/campaign.yaml`
  - `campaign-packs/modified-gravity-action-search/docs/README.md`
  - `campaign-packs/modified-gravity-action-search/docs/provenance.md`
  - `campaign-packs/modified-gravity-action-search/evals/known-models.yaml`
  - `campaign-packs/modified-gravity-action-search/literature-seed.yaml`
  - `campaign-packs/modified-gravity-action-search/skills/action-taxonomy/SKILL.md`
  - `campaign-packs/modified-gravity-action-search/skills/cosmology-reduction/SKILL.md`
  - `campaign-packs/modified-gravity-action-search/skills/literature-xref/SKILL.md`
  - `campaign-packs/modified-gravity-action-search/skills/perturbation-analysis/SKILL.md`
  - `campaign-packs/modified-gravity-action-search/skills/stability-analysis/SKILL.md`
  - `tests/integration/test_campaign_config_integration.py`
- Interfaces Exposed:
  - Campaign-pack contracts for gate skills/templates/evals/literature seed under `campaign-packs/modified-gravity-action-search`.
  - Template assets consumable by `TemplateRegistry.load_directory`.
- Database Changes: none.
- Config Changes:
  - Pack `campaign.yaml` now declares concrete gate timeouts and tool dependencies (`registry`, `scanner`, `arxiv`, `crossref`).
- Depends On: Tasks 3.4 template registry, 5.1 campaign config loader, 5.3 gate pipeline runner.
- Depended On By: Task 7.2 known-model campaign evaluation and pack-level operator workflows.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_modified_gravity_pack.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_modified_gravity_pack.py tests/integration/test_campaign_config_integration.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: `CampaignConfigLoader.load_pack("modified-gravity-action-search")` and `TemplateRegistry.load_directory(...)` consume the pack assets for dry-run gate execution.
  - Integration test: `tests/integration/test_modified_gravity_pack.py` validates install/validate/mock dry-run behavior.

## Task 7.2: End-to-end campaign test with known models

- Files Created:
  - `tests/unit/test_known_models_truth_table.py`
  - `tests/integration/test_known_models_e2e.py`
- Files Modified: none.
- Interfaces Exposed:
  - Known-model mini-campaign truth-table verification contracts.
- Database Changes:
  - Uses existing `eval_results` persistence via `EvalRunner`.
- Config Changes: none.
- Depends On: Task 7.1 known-model eval fixture and Task 1.5 eval runner.
- Depended On By: Phase 7 campaign correctness gate.
- Verification Commands:
  - `.venv/bin/pytest tests/unit/test_known_models_truth_table.py --tb=short -q`
  - `.venv/bin/pytest tests/integration/test_known_models_e2e.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: pack eval suite is executed through `EvalRunner.run_suite(...)` with deterministic model-outcome mapping.
  - Integration test: `tests/integration/test_known_models_e2e.py` enforces zero false positives/negatives for baseline models.

## Task 7.3: Crash recovery test

- Files Created:
  - `tests/integration/test_campaign_crash_recovery.py`
- Files Modified: none.
- Interfaces Exposed:
  - Crash-recovery conformance checks for `CampaignStateMachine.resume(...)` across campaign states.
- Database Changes:
  - No schema changes; exercises persisted campaign/checkpoint/candidate records under restart.
- Config Changes: none.
- Depends On: Task 5.2 campaign state machine and Task 1.6 control plane primitives.
- Depended On By: Phase 7 reliability gate and downstream long-running campaign confidence.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_campaign_crash_recovery.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: resume flow reconstructs run status/metadata after simulated crash boundaries in each supported state path.
  - Integration test: `tests/integration/test_campaign_crash_recovery.py` verifies no candidate corruption and state fidelity on restart.

## Task 7.4: Multi-provider model routing test

- Files Created:
  - `tests/integration/test_multi_provider_routing.py`
- Files Modified: none.
- Interfaces Exposed:
  - Multi-provider equivalence test contract across alternate role-provider configurations.
- Database Changes:
  - Uses existing eval persistence via `EvalRunner` + `CampaignDB`.
- Config Changes: none.
- Depends On: Tasks 1.1 routing, 1.5 eval runner, and Task 7.1 known-model fixture.
- Depended On By: Phase 7 routing-equivalence acceptance gate.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_multi_provider_routing.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: two distinct `ModelRouter` configurations execute the same mini-campaign executor with provider-specific payload normalization and fallback handling.
  - Integration test: `tests/integration/test_multi_provider_routing.py` asserts equivalent model viability outcomes across provider configs.

## Task 7.5: Persona eval suite

- Files Created:
  - `evals/persona-baseline.yaml`
  - `tests/evals/test_persona_evals.py`
- Files Modified: none.
- Interfaces Exposed:
  - Versioned persona eval suite artifact validating §14.4 behavior categories.
- Database Changes:
  - Uses existing eval result persistence through `CampaignDB.add_eval_result`.
- Config Changes: none.
- Depends On: Task 1.5 eval framework and persona/trust guidance docs.
- Depended On By: Phase 7 persona quality gate and regression checks for persona changes.
- Verification Commands:
  - `.venv/bin/pytest tests/evals/test_persona_evals.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: `EvalRunner` loads `evals/persona-baseline.yaml`, executes deterministic persona checks, and persists case outcomes.
  - Integration test: `tests/evals/test_persona_evals.py` enforces pass-threshold and persisted-results coverage.

## Task 7.6: Security audit

- Files Created:
  - `tests/integration/test_security_audit.py`
- Files Modified: none.
- Interfaces Exposed:
  - End-to-end security-audit integration contract for scan, approvals gating, sandbox restrictions, and compaction invariant retention.
- Database Changes: none.
- Config Changes: none.
- Depends On: Task 2.1 security subsystem, Task 2.4 compaction, and CLI scan command surface.
- Depended On By: Phase 7 security acceptance gate.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_security_audit.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
- Consumption Proof:
  - Runtime path: `SecureToolGateway` enforces policy approvals/forbidden operations, `PythonSandboxMCPServer` blocks forbidden imports, and orchestrator compaction retains policy invariant tokens.
  - Integration test: `tests/integration/test_security_audit.py` asserts scan findings, approval/violation behavior, sandbox blocks, and invariant preservation.

## Task 7.7: Documentation and packaging

- Files Created:
  - `src/openeinstein/tools/mcp_entrypoints.py`
  - `tests/integration/test_packaging_install.py`
  - `docs/configuration-reference.md`
  - `docs/campaign-pack-authoring.md`
- Files Modified:
  - `README.md`
  - `pyproject.toml`
- Interfaces Exposed:
  - Console script entrypoints:
    - `openeinstein-mcp-registry`
    - `openeinstein-mcp-sympy`
    - `openeinstein-mcp-mathematica`
    - `openeinstein-mcp-cadabra`
    - `openeinstein-mcp-scanner`
    - `openeinstein-mcp-python-sandbox`
- Database Changes: none.
- Config Changes:
  - Packaging metadata now publishes MCP adapter script entrypoints.
- Depends On: prior tooling/CLI subsystem implementations and Phase 7 campaign/eval deliverables.
- Depended On By: final artifact install validation and operator quickstart onboarding.
- Verification Commands:
  - `.venv/bin/pytest tests/integration/test_packaging_install.py --tb=short -q`
  - `.venv/bin/pytest --tb=short -q`
  - `.venv/bin/ruff check src/ tests/`
  - `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports`
  - `.venv/bin/pip install -e ".[dev]"`
- Consumption Proof:
  - Runtime path: installed console scripts expose MCP adapters and CLI workflows in clean virtualenv installs.
  - Integration test: `tests/integration/test_packaging_install.py` builds wheel/sdist and validates clean-venv install + command surface.
