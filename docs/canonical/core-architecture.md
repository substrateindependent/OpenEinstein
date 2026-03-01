# Core Architecture

## Purpose

OpenEinstein is a local-first gateway runtime for AI-assisted physics research campaigns. The platform is built around a domain-agnostic core and domain-specific campaign packs.

## System Components

- Control Plane: run lifecycle, event stream, pause/resume/stop, approval and policy enforcement
- Campaign Engine: schema-validated campaign config, state machine, checkpoints
- Multi-Agent Layer: orchestrator with optional specialized subagents
- Model Routing: logical role to provider/model resolution with fallbacks
- Tool Bus: unified MCP and CLI+JSON tool execution interface
- Persistence: SQLite tables for run state, traces, evals, approvals
- Tracing + Evals: span capture and deterministic evaluation workflows
- Security Layer: approvals, sandbox policy, and invariant enforcement

## Architectural Invariants

- Core platform contains no physics-subfield-specific logic.
- Domain specialization is delivered through campaign packs.
- Tool access must be mediated by ToolBus.
- Safety constraints are enforced outside LLM context.
- Routing uses logical roles, not hardcoded model IDs.

## Build Sequence Alignment

This architecture is implemented in phases:
- Phase 0: repository bootstrap and foundational docs/policy/persona
- Phase 1+: routing, tools, persistence, tracing, evals, and campaign engine
- Later phases: CAS integration, literature stack, publishing, and packs

## Traceability

- Reference plan: `OpenEinstein-Implementation-Plan.md`
- Reference setup guide: `Development Resources/Repo-Setup-Best-Practices.md`
