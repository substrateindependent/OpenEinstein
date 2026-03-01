# CAS Backends

## Purpose

Defines capability-first symbolic and numerical backend interfaces used by computation gates.

## Core Interfaces

- Backend capability declaration (e.g., symbolic simplify, tensor algebra, numerical solve).
- Session lifecycle controls (start/evaluate/reset/stop).
- Timeout and failure classification contract.
- Deterministic template-to-backend mapping.

## Invariants

- Campaign code declares required capabilities, not specific backend names.
- Backend routing occurs through registry and ToolBus abstractions.
- Timeouts and backend failures are normalized for retry/fallback logic.
