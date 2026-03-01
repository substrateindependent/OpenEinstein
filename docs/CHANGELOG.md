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
- Implemented Phase 3 CAS + numerical stack: SymPy, Mathematica+xAct, Cadabra CLI, template registry, scanner tools, and sandboxed Python execution server.
- Reconciled Cadabra dependency contract to use system CLI runtime (`cadabra2`) instead of a non-existent PyPI package.
- Implemented Phase 4 literature + publishing stack: arXiv, Semantic Scholar, INSPIRE, ADS, CrossRef, Zotero, GROBID ingestion, and LaTeX toolchain/CLI.
- Added canonical literature infrastructure documentation and expanded integration coverage for live connector roundtrips.
- Updated test environment loading to read `.env` for local key-gated integration markers without overriding process env.
- Implemented Phase 5 campaign engine primitives: campaign config loader, state machine with checkpoint/resume, gate pipeline runner, and adaptive sampling.
- Added campaign-phase integration coverage for discovery/validation, crash-restart resume, capability-routed gate execution, and deterministic sampling order.
- Added canonical campaign engine and CLI interface pre-doc updates with phase audit sign-off artifacts.
