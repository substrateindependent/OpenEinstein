# Campaign Engine

## Purpose

Defines canonical runtime contracts for campaign config loading, state transitions, gate execution, and adaptive sampling.

## Core Interfaces

- Campaign config loader validates pack YAML with Pydantic models and capability requirements.
- State machine persists run/candidate progress with checkpoint and resume support.
- Gate pipeline executes deterministic per-candidate stages with timeout and failure classification.
- Adaptive sampling reprioritizes work from observed failure patterns.

## Invariants

- Campaign execution is idempotent across restarts using stable run and candidate identifiers.
- Backend selection is capability-driven; campaign definitions never hardcode CAS providers.
- All campaign side effects are persisted and emitted as control-plane events.
- Campaign data remains isolated by campaign/run scope.
