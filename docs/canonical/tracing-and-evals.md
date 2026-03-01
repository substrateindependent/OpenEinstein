# Tracing and Evals

## Purpose

Tracing captures execution provenance and evals provide deterministic quality checks.

## Interfaces

- `@traced(span_name)` decorator
- `TraceStore.export_otlp_json(...)`
- `EvalRunner.run_suite(...)`

## Invariants

- Traces are persisted with run-level context.
- Eval outputs are stored and reproducible.
