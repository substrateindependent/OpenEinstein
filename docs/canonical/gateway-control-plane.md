# Gateway Control Plane

## Purpose

The control plane manages run lifecycle, event streams, and policy-enforced execution.

## Interfaces

- `ControlPlane.issue_run_id()`
- `ControlPlane.get_status(run_id)`
- `ControlPlane.stream_events(run_id)`
- `ControlPlane.stop(run_id)` / `ControlPlane.resume(run_id)`

## Invariants

- Every event includes run id, timestamp, and type.
- Artifacts are attached to run ids for provenance.
- Policy is enforced before tool execution.
