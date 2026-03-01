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
