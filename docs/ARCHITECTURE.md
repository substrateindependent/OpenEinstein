# Architecture

This document tracks the live architecture of the repository.

## Current State (Through Phase 1)

- Routing subsystem with logical role resolution (`reasoning`, `generation`, `fast`, `embeddings`) and fallback chains.
- ToolBus subsystem with lifecycle-managed tool servers and CLI+JSON adapters.
- SQLite persistence layer with WAL mode, typed CRUD APIs, and migration tracking.
- Tracing subsystem with `@traced` instrumentation and OTLP JSON export.
- Eval framework with Pydantic YAML suite schema, deterministic runner, result persistence, and CLI commands.
- Control plane primitives for run lifecycle (`start/status/wait/events/stop/resume`) with JSONL event streams and artifact attachment.
- Campaign Registry MCP-style server exposing persistence tools through ToolBus.

## Key Boundaries

- Model selection is routed through `openeinstein.routing` by logical role only.
- Tool access is routed through `openeinstein.tools.ToolBus`.
- Policy validation and lifecycle control remain in gateway boundaries.
- Domain-specific logic remains outside core modules.

## Next Phase

Phase 2 expands security enforcement, hooks, and multi-agent orchestration on top of the Phase 1 contracts.
