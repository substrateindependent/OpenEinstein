# OpenEinstein Control UI — UI/UX Strategy

**Version:** 1.0 — March 2026
**Status:** Draft for review
**Audience:** Implementation team (coding agent + PM)

---

## 0. Reference Wireframes

High-fidelity wireframes are provided at `openeinstein-wireframes.html` in the repository root. These wireframes are **inspirational, not prescriptive** — they illustrate the intended information architecture, layout structure, and interaction patterns described in this document, but they are static HTML mockups, not production code.

**What the wireframes show:**

- **Runs list** — table layout with status badges, progress bars, and cost per run
- **Live Run Detail** — three-panel layout (progress tracker / timeline / artifact sidebar) with approval banner, live cost widget, and tool queue visibility
- **Approvals center** — risk-level-coded approval cards with preview/diff, bulk actions, and decision history
- **Artifacts browser** — filterable grid with type icons and provenance metadata
- **New Run wizard** — step-based flow ending in a preflight review with cost/duration estimates
- **Tools panel** — health dashboard with status dots, latency stats, and test buttons
- **Settings** — sidebar navigation with categorized configuration panels

**What the developer is responsible for:**

The wireframes communicate *what* and *why* but not *how*. The implementing developer should:

1. Use the wireframes as a visual north star for layout, information hierarchy, and UX flow — not as pixel-perfect targets.
2. Make all implementation decisions about component architecture, state management, accessibility, responsive behavior, and performance optimization.
3. Deviate from the wireframes wherever technical constraints, accessibility requirements, or better UX patterns warrant it. The wireframes were designed to communicate intent; the developer should apply engineering judgment to realize that intent in production-quality code.
4. Treat the dark color palette and typography in the wireframes as a starting direction. The actual design system (spacing scale, color tokens, type scale) should be built properly with CSS custom properties or a design token system.

---

## 1. Executive Summary

This document refines the original Control UI spec into a build-ready strategy. It preserves the architectural decisions that are well-proven (gateway-serves-SPA, WS+HTTP dual transport, localhost-first security posture) while addressing gaps exposed by stress-testing against OpenClaw's documented failure modes and the broader AI agent dashboard ecosystem.

The key refinements fall into five categories:

1. **Resilience patterns** the original spec omits (disconnection recovery, error states, stale-state prevention)
2. **Cost and token observability** — the single most-complained-about gap in OpenClaw's ecosystem, entirely absent from the original spec
3. **Notification system for long-running work** — researchers cannot stare at a dashboard for hours; the spec assumes they will
4. **Scope reduction for Phase UI-0/UI-1** — the original left nav has 8 items and the event protocol has 10+ message types; both need trimming to ship fast
5. **Concrete data models** for aspirational features (Confidence Panel, Paper Pack) so the coding agent can actually build them

---

## 2. What the Original Spec Gets Right

These decisions are validated by OpenClaw's production experience and should be preserved exactly:

**Gateway-serves-UI pattern.** One process, one port, one deployment artifact. OpenClaw proved this eliminates an entire class of deployment bugs. The UI cannot drift from reality because it is a client to the gateway's actual state machine. Confirmed by the [OpenClaw architecture](https://github.com/openclaw/openclaw).

**WS primary + HTTP secondary.** Live state over WebSocket, idempotent actions and downloads over HTTP. This is the right split. OpenClaw uses the same pattern.

**Localhost-first security posture.** Default bind to `127.0.0.1`, device pairing for new clients, explicit remote access via tunnel. OpenClaw's [security documentation](https://docs.openclaw.ai/gateway/security) validates this — their most common security issue is users exposing port 18789 without TLS.

**"Never hide what actually ran."** This principle directly addresses OpenClaw's [#14797](https://github.com/openclaw/openclaw/issues/14797) (silent empty replies, stuck "thinking" states). Tool calls and artifacts must always be inspectable.

**Phased delivery.** Shipping UI-0 in 1–2 weeks as a read-only dashboard is the right first step. But the phase boundaries need adjustment (see §7).

---

## 3. Stress Test Results — Gaps and Failure Modes

### 3.1 No Disconnection/Reconnection Strategy

**The problem:** The spec defines the WS connect handshake but says nothing about what happens when the connection drops — which it will, especially over SSH tunnels and Tailscale. OpenClaw's [#24903](https://github.com/openclaw/openclaw/issues/24903) documents the exact failure: agent timeout leaves the session in a "stuck" state without user notification.

**Required additions:**

- **Reconnection with exponential backoff.** UI must attempt reconnect automatically (1s, 2s, 4s, 8s, cap at 30s). During reconnect, show a clear "Reconnecting..." banner — not a frozen last-known state.
- **State reconciliation on reconnect.** After reconnecting, the UI sends a `sync_request` with its last-known `eventSeqId`. The gateway responds with a delta of missed events, or a full state snapshot if the gap is too large. This prevents the "stale dashboard" problem.
- **Heartbeat with timeout detection.** Gateway sends `heartbeat` every 15s. If UI receives no message for 45s, it assumes disconnection and enters reconnect mode — don't wait for the TCP stack to notice.
- **Optimistic UI with rollback.** For approval decisions and run control (pause/resume/stop), the UI should show the action immediately, then roll back if the server rejects it on reconnect.

### 3.2 No Cost/Token Observability

**The problem:** This is the single most-complained-about gap in the OpenClaw ecosystem. Users report that sub-agents spawning sub-agents cause costs to spiral with zero visibility. [ClawMetry](https://www.producthunt.com/products/clawmetry) was created as a third-party tool specifically because OpenClaw's built-in dashboard lacked this. The original OpenEinstein spec mentions an "estimated cost/latency badge" in the run wizard but has no live cost tracking.

**Required additions:**

- **Live cost ticker per run.** Displayed prominently in the run header. Updated on every `tool_result` event (which should include `tokenCount` and `estimatedCostUsd` fields).
- **Cost breakdown panel.** Expandable panel showing: tokens by model role (reasoning vs. generation vs. fast), tokens by tool (CAS calls vs. literature search vs. LLM inference), and cumulative cost with a trend line.
- **Budget guard with UI notification.** If `POLICY.json` defines a max cost per run (it should), the UI must show a progress bar toward that limit and fire a notification at 80%.
- **Cost comparison across runs.** In the runs list, show total cost per run so researchers can see which campaigns are expensive.

### 3.3 No Notification System

**The problem:** OpenEinstein campaigns can run for hours. The spec's entire UX assumes the researcher is watching. They won't be. They'll start a campaign, go read a paper, and come back. Without notifications, they'll miss approval requests (blocking the campaign) and completion events.

**Required additions:**

- **Browser notifications (via Notification API).** Request permission on first visit. Fire notifications for: approval required, run completed, run failed, run paused (budget/policy gate), cost warning (80% of budget).
- **Audio cue option.** A subtle chime for approval requests. Toggle in settings. Researchers working late with headphones will appreciate this.
- **Notification center in the top bar.** A badge count of unread events (approvals, errors, completions). Clicking opens a notification drawer.
- **Future: webhook/email.** For Phase UI-2, allow configuring a webhook URL or email for notifications when the browser is closed.

### 3.4 Event Protocol is Too Chatty for CAS-Heavy Runs

**The problem:** A single CAS evaluation (Mathematica simplifying a tensor expression) can involve dozens of subprocess calls, retry loops, and intermediate results. Streaming every `tool_call` and `tool_result` as individual WS messages will overwhelm the UI and the WS buffer during intensive computation phases.

**Required additions:**

- **Event batching.** Gateway should batch events into 100ms windows during high-throughput phases. UI receives a `batch` message containing an array of events, renders them in one paint cycle.
- **Event summarization.** For tool calls below a configurable verbosity threshold, the gateway should send `tool_call_summary` instead of individual call/result pairs. Example: "SymPy: evaluated 47 simplifications in 12.3s, 3 produced non-trivial results."
- **Verbosity levels on the WS.** The UI should be able to send a `set_verbosity` message (`minimal`, `normal`, `verbose`, `debug`) to control how much detail flows over the wire. Default `normal`; researcher can toggle to `verbose` for a specific run.

### 3.5 No Error Recovery UX

**The problem:** The spec defines `error` as a WS message type but says nothing about what the UI does with it. When a CAS kernel crashes, when an MCP server dies, when an API rate-limits — the researcher needs to understand what happened and what their options are.

**Required additions:**

- **Error classification in the UI.** Three tiers: (1) Transient — will auto-retry (show retry count + next attempt time), (2) Blocking — needs human decision (show "Retry / Skip / Abort" actions), (3) Fatal — run cannot continue (show postmortem summary + "Export logs" button).
- **Tool health indicators.** In the Tools panel, show a live status dot (green/yellow/red) per MCP server and CAS backend. If a tool goes unhealthy during a run, the timeline should show it.
- **Graceful degradation messaging.** If the Cadabra backend is unavailable but SymPy can handle the computation (slower, less capable), the UI should show this fallback decision explicitly, not silently swap.

### 3.6 Approval UX Missing Critical Details

**The problem:** The spec's approval flow is good conceptually ("cockpit checklist") but misses operational details that determine whether researchers will actually use it or just rubber-stamp everything.

**Required additions:**

- **Approval queue with priority sorting.** High-risk approvals (shell execution, file writes outside workspace, network fetches) should sort to the top. Low-risk approvals (CAS evaluation, read-only literature search) should be visually distinct (muted styling).
- **Bulk approve for low-risk actions.** "Approve all read-only actions in this run" button. Researchers doing literature campaigns will hate clicking approve 50 times for PubMed queries.
- **Approval timeout with configurable behavior.** The spec mentions `expiresAt` but doesn't define what happens when it expires. Options: (a) auto-deny and continue (safe default), (b) auto-deny and pause, (c) auto-approve (only for whitelisted low-risk actions). This must be configurable per risk level.
- **Approval history per run.** Show a log of all approval decisions (who, when, what) in the run detail view. This matters for reproducibility.

### 3.7 No Run Comparison View

**The problem:** A researcher running a stability analysis campaign will produce dozens of runs with different parameters. The spec treats runs as individual items in a list. There's no way to compare them.

**Required additions (Phase UI-2):**

- **Side-by-side run comparison.** Select 2–5 runs, see: parameter diff, artifact diff, cost comparison, outcome comparison, timeline overlay.
- **Run tagging and filtering.** Let researchers tag runs ("baseline," "high-order," "failed") and filter the run list by tag, status, campaign pack, and date range.

### 3.8 Left Nav is Too Heavy for v1

**The problem:** Eight items in the left nav (Runs, Campaigns, Approvals, Artifacts, Tools, Config, Evals/Traces, Settings) is a lot for a v1 that needs to feel focused. OpenClaw's [#13142](https://github.com/openclaw/openclaw/issues/13142) documents that their dashboard Config/Models/Updates sections are confusing because there's too much surface area with unclear importance hierarchies.

**Refined nav for v1:**

| Phase | Nav Items |
|-------|-----------|
| UI-0 | Runs (with inline approvals), Settings |
| UI-1 | Runs, Approvals, Artifacts, Tools, Settings |
| UI-2 | Add: Campaigns, Evals/Traces |
| UI-3 | Add: Campaign Builder, Pack Marketplace |

Config should live inside Settings, not as a top-level nav item. Evals/Traces is a power feature that belongs in UI-2.

---

## 4. Revised Event Protocol

The original protocol is a good starting point but needs versioning, sequencing, and the additions identified in stress testing.

### 4.1 Message Envelope

Every WS message uses a common envelope:

```json
{
  "v": 1,
  "seq": 42,
  "ts": "2026-03-01T14:30:00.000Z",
  "type": "run_event",
  "payload": { ... }
}
```

- `v`: Protocol version. Allows backward-compatible evolution.
- `seq`: Monotonically increasing sequence number per connection. Used for reconnection delta sync.
- `ts`: Server timestamp (ISO 8601). UI should never rely on client clock.

### 4.2 Message Types (Revised)

**Client → Server:**

| Type | Purpose |
|------|---------|
| `connect` | Auth handshake (token or password + client version) |
| `sync_request` | After reconnect: send last known `seq` to get missed events |
| `approval_decision` | Approve/deny/bulk-approve |
| `set_verbosity` | Control event detail level |
| `run_command` | Start/pause/resume/stop a run |

**Server → Client:**

| Type | Purpose |
|------|---------|
| `connected` | Auth accepted, gateway capabilities, workspace info |
| `sync_response` | Missed events since requested `seq`, or full snapshot |
| `run_state` | Phase, progress percent, ETA, summary, live cost |
| `run_event` | Individual event in the run timeline |
| `tool_call` | Tool invocation with args (redactable) |
| `tool_result` | Tool completion with duration, cost, artifact refs |
| `tool_call_summary` | Batched summary for high-throughput tool phases |
| `approval_required` | Action needing human decision |
| `approval_resolved` | Approval was decided (by human or timeout policy) |
| `cost_update` | Running cost ticker (tokens, USD estimate, budget %) |
| `tool_health` | MCP server or CAS backend status change |
| `error` | Classified error (transient/blocking/fatal) |
| `heartbeat` | Liveness ping (every 15s) |
| `batch` | Array of messages batched during high-throughput phases |

Removed from original: `trace_span` (deferred to UI-2, delivered via HTTP API not WS), `run_event` and `run_state` are clarified as distinct (state is summary, event is timeline item).

### 4.3 Event Storage

Persist all events server-side as JSONL (one file per run). The UI requests historical ranges via HTTP (`GET /api/v1/runs/{id}/events?after_seq=N&limit=100`) and subscribes to live deltas over WS. This means the WS connection only carries new events, not replay.

---

## 5. Revised Auth and Security

### 5.1 Token Storage

**Default: `sessionStorage`**, not `localStorage`. This means the token is lost when the browser tab closes, which is the right default for an admin surface. Provide a "Remember this device" toggle that upgrades to `localStorage` — with a clear warning that this persists the token across sessions.

This directly addresses OpenClaw's [#1690](https://github.com/openclaw/openclaw/issues/1690) (gateway token missing) while being more secure by default.

### 5.2 Device Pairing Flow

1. User opens `http://localhost:{port}/` for the first time.
2. UI shows a "Pair this device" screen with a 6-digit code.
3. The gateway logs the pairing code to stdout (visible in the terminal where `openeinstein` is running).
4. User enters the code in the browser. Gateway issues a device token.
5. Subsequent visits on the same device use the stored token.

For non-local access (detected by checking if the origin is `127.0.0.1` or `localhost`):

6. Gateway requires the connection to be over HTTPS or an SSH tunnel. If it detects plain HTTP from a non-local origin, it refuses the connection with a clear error: "Remote access requires HTTPS. Use `openeinstein dashboard --tunnel` for secure access."

### 5.3 Configuration Surface

```yaml
gateway:
  controlUi:
    enabled: true
    basePath: "/"
    bind: "127.0.0.1"          # Default: localhost only
    port: 8420                   # Default port
    allowedOrigins: []           # For dev server CORS
    allowInsecureRemote: false   # "You're holding a chainsaw" warning if true
    sessionTimeoutMinutes: 480   # 8 hours default
    notificationsEnabled: true
```

---

## 6. Revised UX Specification

### 6.1 Global Layout

> **Wireframe reference:** The overall shell (top bar, left nav, status bar, content area) is visible across all views in `openeinstein-wireframes.html`. The wireframe demonstrates the information density we're aiming for: gateway status and cost in the top bar, notification bell with badge count, collapsible left nav, and a persistent status bar summarizing the active run. The ASCII diagram below is the structural spec; the wireframe is the visual interpretation.

```
┌─────────────────────────────────────────────────────────┐
│ [≡] OpenEinstein    [⌘K Command Palette]  [🔔 3] [⚙]  │
│     Gateway: ● connected    Cost today: $2.14           │
├────────┬────────────────────────────────────────────────┤
│        │                                                │
│  Runs  │   [Main content area]                         │
│        │                                                │
│  ----  │                                                │
│ Apprvl │                                                │
│        │                                                │
│  ----  │                                                │
│ Artfct │                                                │
│        │                                                │
│  ----  │                                                │
│ Tools  │                                                │
│        │                                                │
│  ----  │                                                │
│  [⚙]   │                                                │
│        │                                                │
├────────┴────────────────────────────────────────────────┤
│ [Status bar: active run summary / last event]           │
└─────────────────────────────────────────────────────────┘
```

**Top bar (always visible):**
- Hamburger menu (collapses nav on narrow screens)
- Product name
- Command palette trigger (⌘K)
- Notification bell with unread count
- Settings gear
- Gateway connection status indicator (green dot = connected, yellow = reconnecting, red = disconnected)
- Cumulative cost today (clickable → cost breakdown)

**Status bar (always visible):**
- If a run is active: "Run #12 — Phase: Literature Survey — 34% — ETA: ~8 min — $0.47"
- If idle: "No active runs. Last run: #11 completed 2h ago."

### 6.2 Core Flows (Revised)

#### Flow A: Start a Run

> **Wireframe reference:** See "New Run" view in `openeinstein-wireframes.html` (click "New Run" button or ⌘K palette). The wireframe shows step 3 (Review & Preflight) of the wizard — use it as a guide for information density and layout, not as a rigid template.

**Step 1: Select Campaign Pack**
- Grid of installed packs with icon, name, description, last-used date
- "Install Pack" button (Phase UI-3)

**Step 2: Configure Parameters**
- Schema-driven form generated from the campaign pack's `parameters.json`
- Each parameter shows: label, description, type constraint, default value
- "Advanced" toggle for rarely-changed parameters (progressive disclosure)
- Form validates in real-time against the schema

**Step 3: Review Preflight**
- "What this will do" summary:
  - Tools that will be invoked (with capability flags)
  - Permissions that may be requested (file writes, shell exec, network)
  - Estimated cost range (based on routing config + historical data from similar runs)
  - Estimated duration range
- "Which models will be used" — shows the role→model mapping from routing config

**Step 4: Start**
- Single "Start Run" button
- Immediate redirect to the live run view

#### Flow B: Watch a Run

> **Wireframe reference:** See "Run Detail" view in `openeinstein-wireframes.html` (click any run row). This is the most complex screen — the wireframe demonstrates the three-panel layout, approval banner pattern, timeline event styling, and cost widget placement. The developer should treat the panel proportions and event card designs as directional.

The live run view is the most important screen. It has three panels (collapsible):

**Left panel: Progress tracker**
- Current phase name and description
- Progress bar (real, not fake — based on campaign state machine steps completed vs. total)
- "Next planned step" from orchestrator's plan snapshot
- Active tool calls with spinner and elapsed time
- Queue depth (how many tool calls are pending)
- Retry indicators (if a tool call is being retried, show attempt count)

**Center panel: Timeline**
- Reverse-chronological event stream (newest at top)
- Each event shows: timestamp, icon (tool/approval/error/artifact), one-line summary
- Events are collapsible: click to expand full tool inputs/outputs
- Events are color-coded: blue (info), amber (approval needed), red (error), green (artifact produced)
- "Verbose mode" toggle to show low-level events (individual CAS calls, etc.)
- During high-throughput phases, events are auto-collapsed and a summary row appears: "47 SymPy evaluations in 12.3s — 3 non-trivial results [expand]"

**Right panel: Context sidebar (toggleable)**
- Switches between:
  - **Artifacts**: files produced so far, with inline previews
  - **Cost**: live cost breakdown
  - **Evidence** (Phase UI-2): confidence panel
- Default: Artifacts

#### Flow C: Approvals

> **Wireframe reference:** See "Approvals" view in `openeinstein-wireframes.html` (click "Approvals" in the left nav). The wireframe illustrates the risk-level color coding (red/yellow/green left border), the card layout with what/why/preview sections, the bulk-approve button, and the decision history table. Adapt the card design to work well at different content lengths.

**Approval cards** appear:
1. As a banner at the top of the run view (for the active run)
2. In the dedicated Approvals nav section (for all pending approvals across runs)
3. As a browser notification (if enabled)

Each approval card shows:
- Risk level badge (🟢 low / 🟡 medium / 🔴 high)
- What: "Execute shell command: `wolframscript -file /tmp/verify_metric.wl`"
- Why: "Orchestrator wants to verify the metric signature using Mathematica"
- Preview/diff when relevant (file contents to be written, command to execute)
- Countdown timer showing time until expiry
- Three buttons: **Approve** / **Deny** / **Approve Always** (for this tool+path combo in this run)

**Bulk approval** (for low-risk actions):
- "Approve all pending read-only actions" button when 3+ low-risk approvals are queued
- Requires explicit opt-in toggle in Settings: "Allow bulk approval for low-risk actions"

#### Flow D: Artifacts Browser

> **Wireframe reference:** See "Artifacts" view in `openeinstein-wireframes.html` (click "Artifacts" in the left nav). The wireframe shows a card grid with type-specific icon previews and filter dropdowns. The developer may choose a tree view, a table view, or a grid depending on what works best for the actual artifact volumes researchers will encounter.

- Tree view organized by run, then by artifact type (notebooks, plots, LaTeX, BibTeX, PDFs, CSVs, data files)
- Inline previews:
  - PDF: embedded viewer
  - LaTeX: rendered preview (via KaTeX/MathJax for formulas, full compile preview if LaTeX toolchain available)
  - Plots: image thumbnails (click to enlarge)
  - CSV/data: first 20 rows in a table
  - BibTeX: formatted citation list
- Provenance metadata per artifact:
  - Which tool created it
  - Which run step
  - Input artifact hashes
  - Creation timestamp
  - File hash (SHA-256)
- Download button per artifact and "Download all" per run

#### Flow E: Tools Panel

> **Wireframe reference:** See "Tools" view in `openeinstein-wireframes.html` (click "Tools" in the left nav). The wireframe demonstrates the health-indicator pattern (green/yellow/red dots), the CAS vs. MCP server grouping, and per-tool latency stats. Note the arXiv "degraded" and INSPIRE "down" states as examples of how non-healthy tools should look distinct.

- List of all registered MCP servers and CAS backends
- Per tool: name, status (🟢/🟡/🔴), capabilities list, last health check time
- Expandable detail: connection config, recent invocations, average latency, error rate
- "Test connection" button per tool

### 6.3 Adoption Drivers (Prioritized and De-risked)

The original spec lists 6 "spicy" features. Here they are re-ordered by impact/effort ratio, with de-risking notes:

#### Priority 1: "Paper Pack" Export (Phase UI-1)

This is the single highest-value differentiator because it converts a research run into a tangible, publishable artifact. Ship it early.

**Bundle contents:**
```
paper-pack-{runId}/
├── report.md              # Human-readable summary
├── figures/               # All plots, rendered at publication quality
├── references.bib         # Collected BibTeX
├── main.tex               # LaTeX source (if LaTeX toolchain available)
├── main.pdf               # Compiled PDF (if LaTeX toolchain available)
├── run-manifest.json      # Full reproducibility manifest
│   ├── tool_versions      # Exact versions of every tool used
│   ├── model_routing      # Which models were used for which roles
│   ├── config_hashes      # SHA-256 of all config files
│   ├── parameter_values   # Exact campaign parameters
│   └── event_log_hash     # SHA-256 of the full JSONL event log
└── event-log.jsonl        # Complete event stream for replay
```

**De-risk:** If the LaTeX toolchain is not installed, omit `main.tex` and `main.pdf` and show a note: "Install LaTeX for full paper compilation. See setup guide." The pack is still useful without them.

#### Priority 2: Command Palette (Phase UI-1)

Not "natural language to action" — that's over-engineered for v1. A structured command palette (like VS Code's ⌘K):

**Commands:**
- "Start [campaign name]" — shortcut to start a run
- "Show run [number]" — jump to a run
- "Approve all" — bulk approve low-risk actions
- "Export paper pack for run [number]"
- "Show cost breakdown"
- "Test [tool name] connection"
- "Open settings"

This is fast to build (fuzzy match over a command registry), immediately useful, and lays the groundwork for natural-language commands in UI-2.

#### Priority 3: Run Replay / Inspection (Phase UI-2)

The full "time travel debugging" with scrubbing is ambitious. Ship it in two stages:

**UI-1 (minimal):** Click any event in the timeline → see full tool inputs/outputs and model messages (with token counts) at that step. This is just a detail view, not a replay.

**UI-2 (full):** Scrubable timeline with "re-run from here" that creates a fork run. The fork copies the event log up to the selected point and starts a new run with a locked manifest.

#### Priority 4: Confidence Panel (Phase UI-2)

**Data model (must be defined now so the backend can populate it):**

```json
{
  "runId": "run-123",
  "overallConfidence": 0.73,
  "dimensions": [
    {
      "name": "Algebraic verification",
      "score": 0.95,
      "basis": "3/3 CAS backends agree on metric signature",
      "source": "cas_verification"
    },
    {
      "name": "Literature support",
      "score": 0.61,
      "basis": "4 supporting papers found, 1 contradicting, 2 ambiguous",
      "source": "literature_search"
    },
    {
      "name": "Numerical stability",
      "score": 0.82,
      "basis": "Perturbation analysis stable to 3rd order, 4th order shows sensitivity",
      "source": "numerical_analysis"
    }
  ],
  "weakestLink": "Literature support — contradicting result from Chen et al. (2024) needs human review",
  "humanReviewFlags": [
    "Contradicting citation: Chen et al., PRD 109 (2024) — claims instability in sector III"
  ]
}
```

The UI renders this as a vertical bar chart with color coding (green > 0.8, yellow 0.5–0.8, red < 0.5), plus a callout box for `weakestLink` and `humanReviewFlags`.

#### Priority 5: Schema-Driven Campaign Builder UI (Phase UI-3)

Deferred to UI-3 because it requires the campaign pack schema spec to be finalized and battle-tested through CLI usage first. The principle is right: any pack with a valid schema gets auto-generated parameter forms, structured result tables, and artifact viewer sections. But the schema spec needs to be stable before we generate UI from it.

#### Priority 6: Safe Remote Mode Wizard (Phase UI-2)

Add a Settings panel that walks through remote access options:
- "Use SSH tunnel" with copy-paste command
- "Use Tailscale Serve" with copy-paste command
- Big warning if `allowInsecureRemote` is toggled on

This is lower priority because researchers who need remote access are technical enough to set up tunnels. The big win is the warning when someone tries to bind to `0.0.0.0`.

---

## 7. Revised Phased Delivery Plan

### Phase UI-0: Skeleton + Connectivity (1–2 weeks)

> **Wireframe reference:** The Runs list view and Run Detail view in `openeinstein-wireframes.html` represent what UI-0 should look like when complete (minus the interactive controls, which arrive in UI-1). Use the wireframes to calibrate visual quality expectations for this phase — the read-only dashboard should already feel polished, not scaffolded.

**Goal:** Prove the gateway-serves-SPA pattern works. A researcher can open a browser, see their runs, and watch events stream in real time.

**Deliverables:**
- Vite + React SPA, built to `dist/control-ui/`, served by gateway at `/`
- WebSocket connect/auth/heartbeat/reconnect (with backoff)
- `openeinstein dashboard` CLI command opens the browser (copies OpenClaw's UX win)
- Run list view (read-only): shows all runs with status, start time, duration, cost
- Run detail view (read-only): live event timeline with collapsible event cards
- Gateway status indicator in top bar
- Dark mode support (CSS custom properties, respects `prefers-color-scheme`)

**Tech decisions for UI-0:**
- React (not Lit) — larger hiring ecosystem, better component library support, TypeScript-first
- Tailwind CSS — utility-first, no custom CSS to maintain, dark mode built-in
- Vite — proven by OpenClaw, fast dev server, optimized builds
- Zustand for state — minimal, works well with WS streams
- `reconnecting-websocket` library for WS resilience

**Acceptance criteria:**
- `pip install openeinstein` includes the built UI assets
- `openeinstein dashboard` opens `http://127.0.0.1:8420/` in the default browser
- UI connects via WS, shows gateway version, streams run events in real time
- Disconnecting the network shows "Reconnecting..." banner; reconnecting resumes the stream
- Run list loads historical runs from HTTP API
- Dark mode toggles correctly

### Phase UI-1: Minimum Lovable Dashboard (2–4 weeks)

**Goal:** A researcher can start, monitor, control, and export a campaign entirely from the browser.

**Deliverables:**
- Start Run wizard (campaign pack selection → parameter form → preflight → start)
- Run control: pause / resume / stop buttons (with confirmation for stop)
- Approval center: cards with risk levels, preview/diff, approve/deny/approve-always
- Bulk approval for low-risk actions
- Approval timeout behavior (configurable in Settings)
- Artifacts browser with inline previews (PDF, images, LaTeX formulas, CSV tables)
- Paper Pack export button per run
- Command palette (⌘K) with structured commands
- Live cost ticker per run + cost breakdown panel
- Browser notifications (approval needed, run complete, run failed)
- Notification center in top bar
- Tools panel with health indicators
- Settings page (auth, notifications, approval policies, display preferences)
- Status bar with active run summary

**Acceptance criteria:**
- Researcher can go from "open browser" to "running campaign" in under 60 seconds
- Approval requests appear within 1 second of being issued by the gateway
- Paper Pack downloads as a ZIP with all specified contents
- Cost tracker updates within 2 seconds of each tool completion
- Browser notification fires within 3 seconds of an approval request (when tab is not focused)
- All views work in both light and dark mode

### Phase UI-2: Power + Adoption (4–6 weeks)

**Deliverables:**
- Run replay: click any event → full detail view with tool I/O and model messages
- Run replay: "re-run from here" fork
- Run comparison: side-by-side view for 2–5 runs
- Run tagging and advanced filtering
- Confidence panel (evidence visualization)
- Safe Remote mode wizard in Settings
- Event verbosity controls (minimal/normal/verbose/debug)
- Webhook/email notification configuration
- Evals/Traces nav section (view OpenTelemetry spans, link to Jaeger/Zipkin)
- Keyboard shortcuts for common actions

### Phase UI-3: Platform Magic (6+ weeks)

**Deliverables:**
- Schema-driven campaign builder UI (auto-generated forms from pack schemas)
- Pack marketplace / install UX (with trust tiers and security scanning)
- Natural-language command palette (LLM-backed fuzzy intent matching)
- Dashboard customization (rearrangeable panels, saved layouts)
- Mobile-responsive layout (for checking campaigns from phone over Tailscale)

---

## 8. HTTP API Reference (v1)

All endpoints are prefixed with `/api/v1/`. Auth via `Authorization: Bearer {token}` header.

### Runs

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/runs` | List all runs (paginated, filterable by status/campaign/date) |
| `POST` | `/runs` | Start a new run (body: campaign pack ID + parameters) |
| `GET` | `/runs/{id}` | Get run summary (state, progress, cost, metadata) |
| `POST` | `/runs/{id}/pause` | Pause a run |
| `POST` | `/runs/{id}/resume` | Resume a paused run |
| `POST` | `/runs/{id}/stop` | Stop a run (irreversible) |
| `GET` | `/runs/{id}/events` | Get historical events (paginated, filterable by type/seq range) |
| `GET` | `/runs/{id}/cost` | Get cost breakdown for a run |
| `POST` | `/runs/{id}/export` | Generate Paper Pack (returns download URL when ready) |

### Approvals

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/approvals` | List pending approvals (all runs) |
| `GET` | `/approvals/{id}` | Get approval detail (preview/diff) |
| `POST` | `/approvals/{id}/decide` | Submit decision (approve/deny) |
| `POST` | `/approvals/bulk` | Bulk approve (body: array of approval IDs + decision) |

### Artifacts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/runs/{id}/artifacts` | List artifacts for a run |
| `GET` | `/artifacts/{id}` | Get artifact metadata (provenance, hash) |
| `GET` | `/artifacts/{id}/download` | Download artifact file |
| `GET` | `/artifacts/{id}/preview` | Get preview data (rendered LaTeX, CSV head, etc.) |

### Tools

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tools` | List all MCP servers + CAS backends with status |
| `GET` | `/tools/{id}` | Get tool detail (capabilities, health, recent stats) |
| `POST` | `/tools/{id}/test` | Trigger a health check |

### Config

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/config` | Get current gateway configuration |
| `POST` | `/config/validate` | Validate a proposed config change (dry run) |
| `GET` | `/packs` | List installed campaign packs |

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Gateway health check (for monitoring) |
| `GET` | `/version` | Gateway version + UI version + capabilities |

---

## 9. UX Guardrails

These are non-negotiable principles that apply to every phase:

1. **Progressive disclosure.** Default views show summary information. Details are one click away. Advanced controls are behind toggles. Never show 50 configuration knobs on first load.

2. **Real progress, not fake progress.** Progress bars must reflect actual state machine steps completed vs. total. If the total is unknown, show an indeterminate spinner with elapsed time — never a fake percentage.

3. **Stop and Pause always work.** These buttons must be responsive within 1 second. If the gateway is busy, queue the command and show "Stopping..." immediately. Long-run trust depends entirely on the researcher feeling they can pull the emergency brake.

4. **Treat all external content as untrusted data.** Retrieved papers, tool outputs, API responses — display them as "sources" with provenance metadata, never as raw HTML or executable content. Sanitize all content before rendering.

5. **No silent failures.** If a tool call fails, the UI must show it. If a run stalls, the UI must notice (via heartbeat timeout) and alert the researcher. OpenClaw's silent empty reply problem ([#14064](https://github.com/openclaw/openclaw/issues/14064)) is the canonical example of what to avoid.

6. **Every action is undoable or confirmable.** Destructive actions (stop run, deny approval, delete artifact) require confirmation. Non-destructive actions (pause, change verbosity, toggle view) take effect immediately.

7. **Accessibility basics.** WCAG 2.1 AA compliance: keyboard navigation, focus indicators, sufficient color contrast (especially in the dark theme), screen reader labels for all interactive elements, no information conveyed by color alone.

8. **Performance budget.** Initial load under 500KB gzipped. Time-to-interactive under 2 seconds on localhost. Event rendering must not drop below 30fps even during high-throughput phases (this is why event batching matters).

---

## 10. Open Questions for PM Decision

1. **React vs. Lit?** This document recommends React for hiring ecosystem breadth and component library availability. Lit is smaller and faster but has a narrower talent pool. Decision needed before UI-0.

2. **Port number?** Default `8420` is arbitrary. Should we use a well-known port? Should it be configurable at startup (`openeinstein dashboard --port 9000`)?

3. **Cost estimation model.** How accurate do we need the "estimated cost" badge in the run wizard to be? Options: (a) rough heuristic from routing config (fast, inaccurate), (b) historical average from similar completed runs (accurate after a few runs, cold-start problem), (c) both with progressive refinement.

4. **Approval auto-approve whitelist scope.** Should "approve always for this tool" persist across runs, or only within the current run? Cross-run persistence is more convenient but reduces the security posture.

5. **Paper Pack LaTeX template.** Should we ship a default LaTeX template (e.g., RevTeX4 for physics journals) or let campaign packs provide their own? Recommendation: both — default template with pack override capability.

6. **Telemetry opt-in.** Should the UI include anonymous usage telemetry (crash reports, feature usage stats)? If yes, it must be opt-in with a clear disclosure during first setup. If no, we fly blind on UX issues.

---

## 11. Lessons from OpenClaw (Explicit)

For the implementation team's reference, here are the specific OpenClaw patterns we are deliberately copying and the specific mistakes we are deliberately avoiding:

### Copying

| Pattern | OpenClaw Reference | Why |
|---------|-------------------|-----|
| Gateway serves static SPA | [Control UI docs](https://docs.openclaw.ai/web/control-ui) | One deployment artifact, UI can't drift from backend |
| `openeinstein dashboard` CLI opens browser | OpenClaw's `openclaw` command | Huge usability win for first-time users |
| Device pairing for first connection | [Security docs](https://docs.openclaw.ai/gateway/security) | Right balance of security vs. friction for admin surface |
| Default bind to localhost only | [Security docs](https://docs.openclaw.ai/gateway/security) | Prevents accidental public exposure |
| Vite-based SPA build | OpenClaw uses Vite + Lit | Battle-tested build pipeline |
| WS primary + HTTP secondary | OpenClaw architecture | Right transport split |
| Explicit "insecure remote" warning | OpenClaw warns about HTTP contexts | Prevents security foot-guns |

### Avoiding

| Anti-Pattern | OpenClaw Issue | Our Mitigation |
|--------------|---------------|----------------|
| Silent empty replies / stuck "thinking" | [#14064](https://github.com/openclaw/openclaw/issues/14064), [#14797](https://github.com/openclaw/openclaw/issues/14797) | Heartbeat timeout detection + explicit error states |
| Agent timeout leaves UI stuck | [#24903](https://github.com/openclaw/openclaw/issues/24903) | WS reconnect with state reconciliation |
| No cost/token visibility | Community created ClawMetry for this | Built-in live cost ticker from UI-1 |
| Dashboard config feels unsafe | [#13142](https://github.com/openclaw/openclaw/issues/13142) | Config behind Settings, with validation + dry run |
| Tool call latency spikes invisible | Community reports | Tool health indicators + latency tracking in Tools panel |
| MCP timeout retry loops | [#14797](https://github.com/openclaw/openclaw/issues/14797) | Error classification (transient/blocking/fatal) with explicit retry UX |
| No version indicator in UI | [#13142](https://github.com/openclaw/openclaw/issues/13142) | Version in Settings + `/api/v1/version` endpoint |
| Pairing bugs behind proxies | [#4941](https://github.com/openclaw/openclaw/issues/4941) | Test pairing flow behind reverse proxy in CI |

---

## 12. File Placement

```
src/openeinstein/
├── gateway/
│   ├── api/              # HTTP API route handlers
│   │   ├── runs.py
│   │   ├── approvals.py
│   │   ├── artifacts.py
│   │   ├── tools.py
│   │   ├── config.py
│   │   └── system.py
│   ├── ws/               # WebSocket handler + event protocol
│   │   ├── handler.py
│   │   ├── protocol.py   # Message types + envelope
│   │   ├── auth.py       # Token + device pairing
│   │   └── reconnect.py  # Sync request handling
│   └── ui/               # Static SPA serving
│       └── serve.py      # Serves dist/control-ui/ at basePath
│
ui/                        # Frontend source (separate from Python)
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── stores/           # Zustand stores
│   │   ├── ws.ts         # WebSocket connection + reconnect
│   │   ├── runs.ts       # Run state
│   │   ├── approvals.ts  # Approval queue
│   │   └── notifications.ts
│   ├── components/       # React components
│   │   ├── layout/       # Shell, nav, top bar, status bar
│   │   ├── runs/         # Run list, run detail, timeline
│   │   ├── approvals/    # Approval cards, bulk approve
│   │   ├── artifacts/    # Artifact browser, preview renderers
│   │   ├── tools/        # Tool list, health indicators
│   │   ├── settings/     # Settings panels
│   │   └── common/       # Command palette, notifications, etc.
│   ├── hooks/            # Custom React hooks
│   ├── types/            # TypeScript types (mirroring protocol.py)
│   └── utils/
│
dist/control-ui/           # Built SPA (gitignored, built by CI)
```

The `ui/` directory is a standalone Node project. The build step (`pnpm build`) outputs to `dist/control-ui/`. The Python package includes these built assets. The gateway serves them.
