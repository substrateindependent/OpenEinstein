# Changelog

## 2026-03-01

- Bootstrapped repository structure for OpenEinstein Phase 0.
- Added Python package scaffold and CLI entrypoint.
- Added CI workflow for install + pytest.
- Added root context and contribution docs.
- Added canonical documentation index and core architecture document.
- Added trust model, persona seed, and policy/config scaffolding.
- Implemented Phase 1 model routing with role-based fallback and usage accounting.
- Implemented ToolBus lifecycle manager, CLI+JSON wrapper, and integration roundtrip tests.
- Implemented SQLite persistence typed CRUD + migration APIs with WAL mode.
- Implemented tracing subsystem with decorator instrumentation and OTLP JSON export.
- Implemented eval framework scaffolding with YAML suite schema, runner, CLI, and persisted results.
- Implemented control plane lifecycle primitives with JSONL event stream and artifact attachment.
- Implemented Campaign Registry MCP-style server and ToolBus integration coverage.
- Implemented security subsystem: approvals CLI/state, policy enforcement hook path, secret redaction, metadata pinning, and scanner CLI.
- Implemented hook registry/dispatch with audit and approval built-ins plus non-fatal error handling.
- Implemented skills registry with context budgeting and `openeinstein context report`.
- Implemented base agent abstractions with bootstrap context injection from persona/tools/policy.
- Implemented orchestrator delegation/aggregation with adaptive ordering and invariant-preserving compaction.
- Implemented computation, literature, and verification specialized agent scaffolds with unit/integration coverage.
