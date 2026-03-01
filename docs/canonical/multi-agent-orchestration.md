# Multi-Agent Orchestration

## Purpose

Defines delegation, scheduling, and result aggregation across OpenEinstein agents.

## Core Components

- `OpenEinsteinAgent`: base protocol for model-role and ToolBus-bound execution.
- `Orchestrator`: assigns tasks to sub-agents and aggregates outputs.
- `Context Compactor`: trims context while reinjecting safety and policy invariants.
- `Scheduling Policy`: adjusts execution order based on uncertainty/failure signals.

## Invariants

- All tool access flows through ToolBus.
- Agent model selection uses logical roles via routing.
- Compaction never drops policy/persona invariants.
- Orchestrator failures degrade gracefully and preserve traceability.
