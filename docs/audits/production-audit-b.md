# Production Audit B

## Scope
Architecture and integration-contract conformance after runtime redesign and agent-loop wiring (WP-2 .. WP-4).

## Findings
- Medium: Circular import introduced during cutover (`gateway.runtime_control` <-> `campaigns`).
  - Resolution: switched to direct module import path (`openeinstein.campaigns.executor`) and removed package-init loop.
- Medium: Event replay adapter initially dropped legacy `run_started` events due cache hydration order.
  - Resolution: sync cursor now seeds from persisted JSONL payload `seq` values before runtime event replay.
- Low: CLI compatibility regression for loose campaign manifests.
  - Resolution: adapter fallback to generated default campaign for invalid manifests while retaining requested path metadata.

## Evidence
- Targeted regressions/fixes validated with:
  - `.venv/bin/pytest tests/integration/test_control_plane_cli_integration.py -q`
  - `.venv/bin/pytest tests/integration/test_dashboard_ws_integration.py -q`

## Contract Status
- IC-PR-01 Run Lifecycle: PASS
- IC-PR-02 Campaign Executor: PASS
- IC-PR-03 Agent Loop: PASS
- IC-PR-06 Persistence/Replay: PASS
- IC-PR-11 UI (v2 route exposure): PASS

## Remediation
- Kept compatibility via `ExecutorBackedControlPlane` while routing starts to real executor path.

## Decision
- Go.
