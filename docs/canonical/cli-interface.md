# CLI Interface

## Purpose

Defines the canonical command surface for operating OpenEinstein runs, packs, evaluations, security workflows, and reporting.

## Core Interfaces

- Command namespaces are grouped by subsystem (`run`, `pack`, `eval`, `trace`, `approvals`, `context`, `latex`, `campaign`).
- CLI commands invoke typed subsystem APIs instead of duplicating business logic.
- Commands return deterministic, parseable output where possible and non-zero exit codes on actionable failures.
- Configuration validation and environment checks are exposed through explicit CLI commands.

## Invariants

- CLI remains a thin orchestration boundary over core protocols and services.
- Security policy enforcement and approval checks remain active for tool-executing commands.
- Command additions must include integration coverage for user-facing behavior and exit codes.
- Campaign data-management commands preserve per-campaign isolation boundaries.
