# Architecture

This document tracks the live architecture of the repository.

## Current State (Through Phase 7)

- Routing subsystem with logical role resolution (`reasoning`, `generation`, `fast`, `embeddings`) and fallback chains.
- ToolBus subsystem with lifecycle-managed tool servers and CLI+JSON adapters.
- SQLite persistence layer with WAL mode, typed CRUD APIs, and migration tracking.
- Tracing subsystem with `@traced` instrumentation and OTLP JSON export.
- Eval framework with Pydantic YAML suite schema, deterministic runner, result persistence, and CLI commands.
- Control plane primitives for run lifecycle (`start/status/wait/events/stop/resume`) with JSONL event streams and artifact attachment.
- Campaign Registry MCP-style server exposing persistence tools through ToolBus.
- Security subsystem with approvals store, policy engine enforcement, secret redaction, and metadata pinning.
- Hook dispatch subsystem with built-in approval and audit hooks.
- Skill registry + bounded context assembly with CLI reporting.
- Agent base abstractions and specialized agents:
  - `ComputationAgent`
  - `LiteratureAgent`
  - `VerificationAgent`
  - `AgentOrchestrator`
- CAS and numerical backends exposed through ToolBus:
  - `SympyMCPServer`
  - `MathematicaMCPServer`
  - `CadabraMCPServer`
  - `ScannerMCPServer`
  - `PythonSandboxMCPServer`
- Literature and publishing connectors:
  - `ArxivMCPServer`
  - `SemanticScholarMCPServer`
  - `InspireMCPServer`
  - `ADSMCPServer`
  - `CrossrefMCPServer`
  - `ZoteroMCPServer`
  - `GrobidMCPServer`
  - `LatexToolchain` + `openeinstein latex` CLI surface
- Campaign engine primitives:
  - Campaign pack discovery and schema validation
  - Campaign state machine with checkpoint/resume and idempotency controls
  - Capability-routed gate pipeline with timeout/failure classification
  - Adaptive sampling heuristics from persisted failure patterns
- CLI and reporting surfaces:
  - Expanded operator commands (`init`, `results`, `export`, `config`, `sandbox explain`, `campaign clean`)
  - Pack listing/install flow and LaTeX build alias support
  - `report generate` command with markdown synthesis and optional LaTeX export
- Phase 7 integration completion:
  - First campaign pack (`modified-gravity-action-search`) with concrete skills/templates/evals/docs/seeds
  - Known-model end-to-end truth-table validation
  - Crash recovery coverage across campaign states
  - Multi-provider routing equivalence campaign checks
  - Persona eval suite (`evals/persona-baseline.yaml`) and threshold test coverage
  - Security audit integration pass for scan/approvals/sandbox/compaction invariants
  - Packaging hardening:
    - MCP adapter console scripts (`openeinstein-mcp-*`)
    - Clean-venv wheel/sdist install validation
- Control UI implementation (EPIC-001, partial through UI-009):
  - FastAPI dashboard app factory at `openeinstein.gateway.web.create_dashboard_app`
  - HTTP API v1 routers under `openeinstein.gateway.api`:
    - pairing auth (`/api/v1/pair/*`)
    - runs lifecycle (`/api/v1/runs*`)
    - approvals/artifacts/tools/config/system surfaces
  - WebSocket control endpoint at `/ws/control` with typed message handling and heartbeat/sync support
  - Dashboard auth subsystem (`openeinstein.gateway.auth`) with pairing-code issuance and bearer token validation
  - In-memory event sequencing hub (`openeinstein.gateway.events`) for WS sync replay
  - CLI dashboard server command (`openeinstein dashboard`)
  - React/Vite frontend workspace in `ui/` with route shell + Zustand stores wired to API/WS
  - Frontend build artifacts emitted to `dist/control-ui` and served by gateway

## Key Boundaries

- Model selection is routed through `openeinstein.routing` by logical role only.
- Tool access is routed through `openeinstein.tools.ToolBus`.
- Policy validation and lifecycle control remain in gateway boundaries.
- Domain-specific logic remains outside core modules.

## Status

Sequential task execution from 0.1 through 7.7 is implemented and validated in-repo.  
UI epic implementation is active, with foundational backend/frontend contracts through UI-009 complete.
