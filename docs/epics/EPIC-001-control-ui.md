# EPIC-001 Control UI

## Goal

Implement the full dashboard strategy from `docs/UI-UX-STRATEGY.md` with a single-process gateway-served SPA, authenticated HTTP/WS control plane surfaces, and integration-verified wiring.

## Scope

- Phases UI-0 through UI-3 (tickets UI-001..UI-024).
- Backend: gateway web app, HTTP API v1, WS protocol v1, pairing auth, paper-pack export.
- Frontend: React/Vite control UI, state stores, routing, dashboards, approvals, artifacts, tools, advanced views.
- Packaging and CI wiring for `dist/control-ui`.

## Non-Scope

- Physics-domain logic in core modules.
- Direct tool/provider calls from UI code.
- Telemetry collection.

## Integration Contract Matrix

| Contract | Summary | Runtime Path | Integration Test ID |
|---|---|---|---|
| IC-01 | CLI dashboard entrypoint registered and reachable | `openeinstein.cli.main:dashboard` command dispatches to gateway server boot path | `TEST-IC-01-cli-dashboard` |
| IC-02 | Dashboard app factory and DI wiring | `openeinstein.gateway.web.app:create_dashboard_app` resolves `DashboardDeps` and mounts API/WS/static | `TEST-IC-02-app-factory-di` |
| IC-03 | Static SPA mount and fallback routing | ASGI static mount serves `dist/control-ui/index.html` and fallback path handler | `TEST-IC-03-static-fallback` |
| IC-04 | Auth pairing/token validation on HTTP+WS | `openeinstein.gateway.auth` token dependency used by API routers and WS connect handshake | `TEST-IC-04-auth-http-ws` |
| IC-05 | WS endpoint protocol registration | `openeinstein.gateway.ws.handler` mounted at `/ws/control` and handles typed client messages | `TEST-IC-05-ws-route-protocol` |
| IC-06 | Event sequencing/heartbeat/reconnect/batching | `openeinstein.gateway.events` feeds WS stream with `seq`, heartbeat timer, delta sync and batches | `TEST-IC-06-stream-resilience` |
| IC-07 | Runs API wired to lifecycle services | `/api/v1/runs*` routes call control plane and campaign state interfaces | `TEST-IC-07-runs-api-wiring` |
| IC-08 | Approvals API wired to approvals/policy | `/api/v1/approvals*` routes call approvals store and policy gate logic | `TEST-IC-08-approvals-api-wiring` |
| IC-09 | Artifacts API wired to artifact storage and preview | `/api/v1/runs/{id}/artifacts`, `/api/v1/artifacts/{id}*` resolve persisted artifact metadata/content | `TEST-IC-09-artifacts-api-wiring` |
| IC-10 | Tools API wired to ToolBus health/test | `/api/v1/tools*` routes call ToolBus registry and test-call path | `TEST-IC-10-tools-api-wiring` |
| IC-11 | Config/system API wired to runtime metadata | `/api/v1/config*`, `/api/v1/health`, `/api/v1/version` return validated runtime config/capabilities | `TEST-IC-11-config-system-wiring` |
| IC-12 | Paper Pack export route wired to report/latex | `/api/v1/runs/{id}/export` triggers paper-pack service and returns downloadable artifact | `TEST-IC-12-export-wiring` |
| IC-13 | UI router/nav mounts required views | `ui/src/App.tsx` and route modules register views and nav entrypoints | `TEST-IC-13-route-mounting` |
| IC-14 | Frontend stores wired to HTTP bootstrap + WS deltas | Zustand stores hydrate from API client and subscribe/apply WS updates | `TEST-IC-14-store-dataflow` |
| IC-15 | Notification emitter/subscriber path | Gateway event classes map to notification store and browser notification triggers | `TEST-IC-15-notification-pipeline` |
| IC-16 | Command palette registry wiring | Palette command registry executes route transitions and API calls | `TEST-IC-16-command-palette-dispatch` |
| IC-17 | Replay/compare/confidence views wired | UI advanced views call backend compare/replay/confidence endpoints | `TEST-IC-17-advanced-view-dataflow` |
| IC-18 | Remote wizard and webhook/email settings wiring | Settings UI calls backend config/event notification endpoints and reflects validation results | `TEST-IC-18-remote-webhook-wiring` |
| IC-19 | Campaign builder and marketplace wiring | Builder and marketplace surfaces call pack schema/discovery/install/scan APIs | `TEST-IC-19-builder-marketplace-wiring` |
| IC-20 | NL command routing respects model roles + ToolBus boundaries | NL command endpoint routes through role-based router and policy-gated tool dispatch path | `TEST-IC-20-nl-command-guardrails` |
| IC-21 | Packaging includes built UI assets | Python build includes `dist/control-ui` and installed package serves UI entrypoint | `TEST-IC-21-packaging-assets` |
| IC-22 | No-orphan guard for new interfaces | Each added interface has runtime call path + integration test consumer in this matrix | `TEST-IC-22-no-orphan-check` |

## Ticket Map

| Ticket | Phase | Primary Contracts |
|---|---|---|
| UI-001 | A | IC-22 |
| UI-002 | A | IC-13, IC-21, IC-22 |
| UI-003 | A | IC-02, IC-03, IC-11, IC-21, IC-22 |
| UI-004 | A | IC-01, IC-02, IC-21, IC-22 |
| UI-005 | B | IC-04, IC-11, IC-22 |
| UI-006 | B | IC-05, IC-06, IC-14, IC-22 |
| UI-007 | B | IC-07, IC-08, IC-09, IC-10, IC-11, IC-12, IC-22 |
| UI-008 | C | IC-13, IC-22 |
| UI-009 | C | IC-14, IC-15, IC-22 |
| UI-010 | C | IC-06, IC-07, IC-13, IC-14, IC-22 |
| UI-011 | C | IC-06, IC-13, IC-14, IC-22 |
| UI-012 | D | IC-07, IC-13, IC-14, IC-16, IC-22 |
| UI-013 | D | IC-08, IC-14, IC-15, IC-22 |
| UI-014 | D | IC-09, IC-12, IC-13, IC-22 |
| UI-015 | D | IC-06, IC-14, IC-15, IC-22 |
| UI-016 | D | IC-10, IC-11, IC-15, IC-22 |
| UI-017 | D | IC-16, IC-13, IC-22 |
| UI-018 | E | IC-06, IC-16, IC-17, IC-22 |
| UI-019 | E | IC-07, IC-11, IC-17, IC-22 |
| UI-020 | E | IC-11, IC-15, IC-18, IC-22 |
| UI-021 | F | IC-19, IC-13, IC-22 |
| UI-022 | F | IC-19, IC-10, IC-11, IC-22 |
| UI-023 | F | IC-20, IC-13, IC-16, IC-22 |
| UI-024 | G | IC-21, IC-22 |

## Verification Matrix

| Layer | Command |
|---|---|
| Python tests | `.venv/bin/pytest --tb=short -q` |
| Python lint | `.venv/bin/ruff check src/ tests/` |
| Python types | `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports` |
| Frontend tests | `pnpm test` |
| Frontend types | `pnpm run typecheck` |
| Frontend build | `pnpm build` |
| Packaging smoke | `.venv/bin/python -m build` and clean-venv install check |

## Wiring Criteria Enforcement

Each ticket that introduces an artifact must include:

1. A runtime invocation path (CLI route, API handler, WS subscription, mounted component, or store subscriber).
2. A dedicated integration test that validates the path is actively invoked.
3. Ledger update in `docs/build-plans/integration-contract-ledger.md` proving call graph connectivity.

## Build Status (Current)

### Completed Tickets

- UI-001: Epic spec and integration-contract scaffold.
- UI-002: Frontend workspace (`ui/`) with Vite/React/TS, Zustand, Vitest/RTL, Playwright, root pnpm scripts.
- UI-003: Gateway dashboard app factory and SPA static/fallback serving.
- UI-004: `openeinstein dashboard` CLI command with host/port/base-path/no-open options.
- UI-005: Pairing + bearer-token auth service and protected API dependency.
- UI-006: WS `/ws/control` route with connect/sync/run_command/heartbeat handling.
- UI-007: API v1 baseline routers for runs/approvals/artifacts/tools/config/system/export.
- UI-008: App shell + route/nav mounting for Runs and Settings.
- UI-009: Frontend data plumbing baseline (API client + session/runs/ws stores and live wiring).
- UI-010: Run detail three-panel workflow with selectable timeline and live event rendering.
- UI-011: Reconnect/error UX surfaced in shell with classified error stack and gateway-state banner.
- UI-012: Start run wizard + lifecycle controls (pause/resume/stop) with API mutation wiring.
- UI-013: Approvals center + inline approval banner with risk sorting and decision/bulk-decision wiring.
- UI-014: Artifacts browser + preview flow + Paper Pack export/download wiring.
- UI-015: Cost observability and notification fan-out (`cost_update` to top bar/run panel/status/notifications).
- UI-016: Tools panel + settings surface with test-connection and config validation wiring.
- UI-017: Command palette with keyboard shortcut (`Cmd/Ctrl+K`), navigation commands, and mutation command dispatch.
- UI-018: Run replay/inspection baseline with event inspector, fork-from-event API flow, and runtime verbosity controls over WS.
- UI-019: Compare route with run selection, tag/filter controls, confidence panel, and compare/tag API wiring.

### In Progress / Not Yet Implemented

- UI-020 through UI-024 remain open (remote+webhook wizard, campaign builder + marketplace, NL command mode/layout customization, packaging/CI hardening).

### Key Files Changed

- Backend:
  - `src/openeinstein/gateway/web/*`
  - `src/openeinstein/gateway/api/*`
  - `src/openeinstein/gateway/ws/*`
  - `src/openeinstein/gateway/auth.py`
  - `src/openeinstein/gateway/events.py`
  - `src/openeinstein/cli/main.py`
  - `src/openeinstein/gateway/control_plane.py`
  - `src/openeinstein/tools/tool_bus.py`
- Frontend:
  - `ui/src/App.tsx`
  - `ui/src/components/commands/CommandPalette.tsx`
  - `ui/src/components/approvals/ApprovalsCenter.tsx`
  - `ui/src/components/runs/ApprovalBanner.tsx`
  - `ui/src/components/artifacts/ArtifactsBrowser.tsx`
  - `ui/src/components/tools/ToolsPanel.tsx`
  - `ui/src/components/settings/SettingsPanel.tsx`
  - `ui/src/stores/*`
  - `ui/src/lib/apiClient.ts`
  - `ui/src/types/*`
  - `ui/vite.config.ts`
  - `ui/package.json`

### Verification Snapshot

- `pnpm test` passes.
- `pnpm run typecheck` passes.
- `pnpm run build` passes and outputs `dist/control-ui`.
- `.venv/bin/pytest --tb=short -q` passes.
- `.venv/bin/ruff check src/ tests/` passes.
- `.venv/bin/mypy src/openeinstein/ --ignore-missing-imports` passes.
