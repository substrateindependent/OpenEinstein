# Architecture

This document tracks the live architecture of the repository.

## Current State (Through Phase 6)

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

## Key Boundaries

- Model selection is routed through `openeinstein.routing` by logical role only.
- Tool access is routed through `openeinstein.tools.ToolBus`.
- Policy validation and lifecycle control remain in gateway boundaries.
- Domain-specific logic remains outside core modules.

## Next Phase

Phase 7 finalizes first campaign pack execution and end-to-end integration validation.
