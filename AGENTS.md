# OpenEinstein Agent Context

## Project Summary

OpenEinstein is a local-first AI research platform for theoretical physics. The core platform is domain-agnostic; specialization belongs in Campaign Packs.

## Architecture Rules

- Use logical model roles (`reasoning`, `generation`, `fast`, `embeddings`), never hardcoded model IDs in feature logic.
- Route all model selection through the model routing subsystem.
- Route all tool calls through ToolBus abstractions. Do not call MCP/CLI tools directly from domain logic.
- Keep core platform generic; put physics-subfield specifics in `campaign-packs/`.
- Prefer protocol/interface boundaries for subsystems (gateway, routing, tools, persistence, tracing).

## Tech Stack

- Python 3.12+
- Pydantic / PydanticAI / LiteLLM
- MCP SDK + CLI+JSON tool wrappers
- SQLite (default persistence)
- Typer (CLI)
- OpenTelemetry-compatible tracing
- Pytest for testing

## Repository Capabilities Map

- `src/openeinstein/core`: core contracts and canonical persona
- `src/openeinstein/gateway`: control plane, approvals, policy enforcement
- `src/openeinstein/agents`: orchestrator and specialized subagent definitions
- `src/openeinstein/tools`: ToolBus, MCP connection management, tool registry
- `src/openeinstein/campaigns`: campaign config, state machine, execution engine
- `src/openeinstein/routing`: role-based model routing and fallback policies
- `src/openeinstein/persistence`: SQLite tables, migrations, typed CRUD APIs
- `src/openeinstein/tracing`: span instrumentation and exporters
- `src/openeinstein/evals`: eval suite schemas and runners
- `src/openeinstein/security`: approvals, sandbox policy, invariants
- `src/openeinstein/cli`: CLI commands for run/control/reporting

## Global Conventions

- Keep imports stable and explicit; avoid circular imports.
- Prefer typed function signatures and Pydantic models at boundaries.
- Keep modules small and cohesion high by subsystem.
- Put experimental or domain-specific logic into campaign packs.
- Keep docs and integration contracts updated with structural changes.

## Anti-Patterns (Do Not Introduce)

- Hardcoded provider/model names in business logic
- Direct calls to provider SDKs from agent code
- Direct subprocess/MCP calls bypassing ToolBus
- Policy checks implemented only in prompt text (must be machine-enforced)
- Campaign-specific physics heuristics embedded into core platform modules

## Testing Requirements

- Add or update unit tests for every new subsystem behavior.
- Add integration tests for cross-subsystem wiring (routing, tool bus, persistence, tracing).
- Add eval fixtures for persona, safety, and campaign regression when behavior changes.
- Run `pytest` before merging.

## Documentation Workflow

- Canonical docs live in `docs/canonical/`.
- Architectural decisions live in `docs/decisions/` as ADRs.
- Build plans live in `docs/build-plans/`.
- Keep `AGENTS.md` semantically aligned with this file.

## Build Execution Rules

**READ `BUILD-READY.md` BEFORE BEGINNING ANY IMPLEMENTATION WORK.**

It contains the frozen decisions for:
- Core vs. plugin scope (what must pass CI vs. what gets skip-marked)
- Build environment contract (available tools and dependencies)
- Credentials and secrets (`.env` structure and key requirements per phase)
- Verification loop (exact commands to run after every task)
- Stop conditions (when to halt and ask for help)
- Agent kickoff instructions (execution order, commit discipline, architecture guards)

Test skip markers for optional dependencies live in `tests/conftest.py`.

## Living Error Log

1. Missing machine-enforced safety checks.
   Fix: Encode safety invariants in `configs/POLICY.json` and enforce in gateway hooks.
2. Model/provider coupling introduced in feature code.
   Fix: Add/extend logical role routing config and resolve roles centrally.
3. Cross-domain logic leaked into core.
   Fix: Move domain specifics into campaign packs and expose extension hooks.
