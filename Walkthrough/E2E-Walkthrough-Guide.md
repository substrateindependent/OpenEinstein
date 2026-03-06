# OpenEinstein E2E Walkthrough Guide

**Purpose:** Manual browser-test checklist covering the full platform from a user-story perspective. Each section represents a user flow that a physicist would actually perform. Test in order — later flows depend on state created by earlier ones.

**Setup:** Start the dashboard with `openeinstein dashboard --port 8420` and open `http://localhost:8420` in your browser. Have a terminal open alongside for CLI verification.

---

## Flow 1: First Launch & Authentication

**User Story:** *As a researcher, I want to launch the dashboard and authenticate so I can manage my campaigns from a browser.*

**PM Intent:** First contact should feel professional and zero-friction. The pairing flow exists because the gateway runs locally but may be accessed from another device on the same network. It should feel like pairing a TV app — simple, fast, trustworthy.

### Steps

- [ ] **1.1** Run `openeinstein dashboard --port 8420` in terminal. Confirm:
  - Terminal prints bind address and port
  - Browser opens automatically (unless `--no-open`)
  - No crash, no unhandled exceptions in terminal

- [ ] **1.2** Dashboard loads with a pairing/auth screen (if auth is enabled). Confirm:
  - A 6-digit pairing code is displayed (or the dashboard loads directly if auth is disabled)
  - The UI is clean and responsive — no broken layouts or missing assets

- [ ] **1.3** Complete pairing (if applicable). Confirm:
  - After entering the code, the dashboard transitions to the main view
  - WebSocket connection indicator shows "connected" (check browser console or status bar)
  - No auth errors in terminal logs

- [ ] **1.4** Check system health. Confirm:
  - `GET /api/v2/health` returns 200
  - `GET /api/v2/version` returns gateway version, UI version, protocol version
  - `GET /api/v2/system` returns config with base_path, bind address, port

**CLI Cross-Check:**
```bash
openeinstein version
# Should match the version shown in the dashboard
```

---

## Flow 2: Runs Dashboard — Overview & Empty State

**User Story:** *As a researcher, I want to see all my campaign runs at a glance so I know what's running, what completed, and what failed.*

**PM Intent:** The runs dashboard is the home screen. It should communicate status instantly — a researcher glancing at it during lunch should know whether their overnight campaign succeeded or needs attention. Empty state should guide, not confuse.

### Steps

- [ ] **2.1** Navigate to the home route (`/`). Confirm:
  - The runs list is displayed (may be empty on first use)
  - If empty, there is a clear call-to-action or guidance (not a blank page)
  - Layout matches screenshot `01-runs-overview.png`

- [ ] **2.2** Verify the runs API returns data. Confirm:
  - `GET /api/v2/runs` returns a JSON array (possibly empty)
  - Response includes run metadata fields: `run_id`, `status`, `started_at`, `updated_at`

---

## Flow 3: Starting a Campaign Run

**User Story:** *As a researcher, I want to start a new campaign from either the CLI or the dashboard so I can begin exploring a theoretical search space.*

**PM Intent:** Starting a run should be as simple as pointing at a campaign.yaml. The system does the rest — validates config, loads the Campaign Pack, and begins executing. The researcher gets a run_id they can use everywhere.

### Steps (CLI)

- [ ] **3.1** Start a campaign from CLI:
  ```bash
  openeinstein run start campaign-packs/scalar-tensor-lab/campaign.yaml
  ```
  Confirm:
  - A `run_id` is printed (e.g., `run_20260305_001`)
  - No schema validation errors
  - Terminal shows the run entering CONFIGURING then INITIALIZED state

- [ ] **3.2** Verify the run appears in the dashboard. Confirm:
  - Refresh the runs page — the new run appears in the list
  - Status shows "running" (or the current state)
  - Timestamp is correct

### Steps (Dashboard)

- [ ] **3.3** Navigate to the Campaign Builder page (`/builder`). Confirm:
  - Builder UI loads with pack selection or config editor
  - Layout matches screenshot `10-builder-schema.png`

- [ ] **3.4** Start a run from the builder. Confirm:
  - Configure a campaign (select pack, set parameters)
  - Click "Start Run" (or equivalent)
  - Run starts successfully — confirmation shown in UI
  - Layout matches screenshot `11-builder-run-started.png`

- [ ] **3.5** Verify the run via API:
  ```bash
  curl http://localhost:8420/api/v2/runs
  ```
  Confirm: The new run appears with correct campaign path and status.

**CLI Cross-Check:**
```bash
openeinstein run status
# Should show the most recent run's status
```

---

## Flow 4: Real-Time Event Streaming

**User Story:** *As a researcher, I want to watch my campaign's progress in real time — seeing tool calls, state transitions, and candidate evaluations as they happen — so I can intervene if something goes wrong.*

**PM Intent:** This is where the researcher feels in control. Live events streaming should feel like watching a build log — constant, informative, never stale. WebSocket reliability is critical; if the connection drops, it should reconnect transparently. The event stream is the system's heartbeat.

### Steps

- [ ] **4.1** With a run active, observe the dashboard's event stream. Confirm:
  - Events appear in real time (not polling — WebSocket-driven)
  - Event types visible: `state_transition`, `tool_call`, `tool_result`, `agent_spawn`, etc.
  - Each event shows timestamp, type, and payload summary

- [ ] **4.2** Stream events from CLI:
  ```bash
  openeinstein run events <run_id>
  ```
  Confirm:
  - JSONL events stream to stdout in tail -f style
  - Events match what the dashboard shows
  - Ctrl+C cleanly stops the stream

- [ ] **4.3** Test WebSocket reconnection. Confirm:
  - Disconnect WiFi or close/reopen browser tab
  - Dashboard reconnects and picks up the event stream (sync_request with last_seq)
  - No events are lost

- [ ] **4.4** Test verbosity control via WebSocket. Confirm:
  - Change verbosity level (normal / verbose / debug) if UI control exists
  - Event detail level changes accordingly

---

## Flow 5: Run Lifecycle Control (Pause / Resume / Stop)

**User Story:** *As a researcher, I want to pause a running campaign to inspect intermediate results, then resume it later — or stop it entirely if the approach isn't working.*

**PM Intent:** The researcher must feel that they can always interrupt and inspect without losing work. Pause should be graceful (finish the current gate/step, then halt). Resume should pick up exactly where it left off — no re-running completed work. Stop is permanent. These controls exist because research is iterative: you look at early results, adjust, and continue.

### Steps

- [ ] **5.1** Pause a running campaign from the dashboard. Confirm:
  - Click the pause button on a running run
  - Run transitions to "paused" state (may complete current step first)
  - Events stream shows `state_transition` to paused
  - Layout matches screenshot `02-runs-control-resume.png`

- [ ] **5.2** Verify pause via CLI:
  ```bash
  openeinstein run status <run_id>
  # Should show "paused" or "stopped" state
  ```

- [ ] **5.3** Resume the paused campaign from the dashboard. Confirm:
  - Click the resume button
  - Run transitions back to an active state
  - Event stream resumes from where it left off
  - No duplicate work (events continue from last checkpoint, not from the beginning)

- [ ] **5.4** Resume from CLI:
  ```bash
  openeinstein run resume <run_id>
  ```
  Confirm: Run resumes and status updates in both CLI and dashboard.

- [ ] **5.5** Stop a running campaign. Confirm:
  - Use `openeinstein run stop <run_id>` or the dashboard stop button
  - Run enters terminal state (stopped/completed)
  - Cannot be resumed after stop (stop is permanent)

- [ ] **5.6** Verify state persistence. Confirm:
  - Restart the dashboard process (`Ctrl+C` and relaunch)
  - All run history is preserved (SQLite persistence)
  - Completed/stopped runs still visible with correct status and artifacts

---

## Flow 6: Approvals — Human-in-the-Loop Safety

**User Story:** *As a researcher, I want the system to ask my permission before running risky operations (shell commands, network fetches, filesystem writes) so I stay in control of what the agent does on my machine.*

**PM Intent:** This is a core trust mechanism. The PM's philosophy is "default-deny, explicit-approve." The system should never surprise the researcher with unexpected side effects. Approvals are auditable — every grant/revoke is logged with timestamp and reason. The UI should make pending approvals impossible to miss.

### Steps

- [ ] **6.1** Navigate to the Approvals page (`/approvals`). Confirm:
  - Page loads showing pending and resolved approvals
  - Layout matches screenshot `03-approvals-pending.png`

- [ ] **6.2** Trigger an approval request (run a campaign that requires shell_exec or similar). Confirm:
  - A pending approval appears in the dashboard
  - It shows: what action is requested, why, risk level
  - The run is blocked until the approval is resolved

- [ ] **6.3** Approve a pending request from the dashboard. Confirm:
  - Click approve/grant on the pending approval
  - The approval resolves and the blocked tool call proceeds
  - Layout matches screenshot `04-approvals-cleared.png`

- [ ] **6.4** Verify approvals via CLI:
  ```bash
  openeinstein approvals list
  # Should show the granted approval
  ```

- [ ] **6.5** Test bulk approvals (if multiple pending). Confirm:
  - Select multiple pending approvals
  - Bulk approve/reject works correctly
  - All selected approvals resolve atomically

- [ ] **6.6** Revoke an approval:
  ```bash
  openeinstein approvals revoke shell_exec
  ```
  Confirm: The approval is removed. Future calls to that tool will require re-approval.

- [ ] **6.7** Reset all approvals:
  ```bash
  openeinstein approvals reset
  ```
  Confirm: All approvals cleared. Dashboard reflects the reset.

---

## Flow 7: Artifacts — Viewing Research Outputs

**User Story:** *As a researcher, I want to browse and download the artifacts my campaign produced — CAS notebooks, derivations, plots, LaTeX files — so I can review the work and use it in my publications.*

**PM Intent:** Artifacts are the tangible output of a campaign. The researcher should be able to find, preview, and download any artifact without digging through filesystem paths. Preview should work inline for common formats (text, images, PDFs). The artifact trail should be complete — every computation, every derivation, linked back to the run that produced it.

### Steps

- [ ] **7.1** Navigate to the Artifacts page (or artifacts tab within a run detail view). Confirm:
  - Artifacts listed with name, type, and timestamp
  - Layout matches screenshot `05-artifacts-before-export.png`

- [ ] **7.2** Preview an artifact. Confirm:
  - Click on a text/image/PDF artifact
  - Preview renders inline (text shown, images displayed, PDFs embedded)
  - `GET /api/v2/artifacts/{artifact_id}/preview` returns content with correct mode

- [ ] **7.3** Download an artifact. Confirm:
  - Click download on an artifact
  - File downloads correctly with the right filename and content
  - `GET /api/v2/artifacts/{artifact_id}/download` serves the file

- [ ] **7.4** Export a run as a paper pack:
  - From the run detail view, click "Export" (or use API)
  - `POST /api/v2/runs/{run_id}/export` returns the export package
  - Layout matches screenshot `06-artifacts-exported-preview.png`

---

## Flow 8: Run Comparison & Tagging

**User Story:** *As a researcher running multiple campaigns with different parameters, I want to compare runs side-by-side and tag them for organization so I can track which approach worked best.*

**PM Intent:** Research is iterative. A physicist might run the same campaign 5 times with different model configurations, parameter ranges, or gate thresholds. Comparison should surface the differences that matter: candidate counts, gate pass rates, costs, timing. Tags are the researcher's own organizational system — the platform should support it, not impose one.

### Steps

- [ ] **8.1** Tag a run from the dashboard. Confirm:
  - Click on a run, add tags (e.g., "baseline", "high-budget", "ollama-test")
  - Tags persist across page refreshes
  - `POST /api/v2/runs/{run_id}/tags` updates correctly

- [ ] **8.2** Navigate to the Compare view (`/compare`). Confirm:
  - Select 2+ runs for comparison
  - Side-by-side metrics displayed (cost, duration, candidates, gate results)
  - Layout matches screenshot `07-compare-and-tag.png`

- [ ] **8.3** Verify compare API:
  ```bash
  curl "http://localhost:8420/api/v2/runs/compare?run_ids=<id1>,<id2>"
  ```
  Confirm: Returns comparison data for the specified runs.

---

## Flow 9: Tools Status & Testing

**User Story:** *As a researcher, I want to see which tools (MCP servers, CAS kernels, literature APIs) are available and test them before starting a long campaign, so I don't waste hours on a run that will fail because Mathematica isn't configured.*

**PM Intent:** Tool availability is a prerequisite for campaign success. The researcher should be able to verify their entire toolchain is healthy before committing to a multi-hour run. Testing a tool should give immediate, unambiguous feedback: working or not, and why not.

### Steps

- [ ] **9.1** Navigate to the Tools page (`/tools`). Confirm:
  - All configured tool servers listed with status (connected/disconnected/error)
  - Layout matches screenshot `08-tools-page.png`

- [ ] **9.2** Test a tool server. Confirm:
  - Click "Test" on a tool entry
  - Test runs and shows pass/fail result
  - `POST /api/v2/tools/{tool_id}/test` returns status

- [ ] **9.3** Verify tools via API:
  ```bash
  curl http://localhost:8420/api/v2/tools
  ```
  Confirm: Returns list of tools with their current status.

---

## Flow 10: Settings, Validation & Integrations

**User Story:** *As a researcher, I want to configure my model routing, webhook notifications, and email alerts from the dashboard so I can customize OpenEinstein to my workflow without editing YAML files manually.*

**PM Intent:** Configuration should be accessible but safe. Validation catches errors before they cause runtime failures. The settings page is where the researcher controls the "operational" side of the platform — not the science, but the infrastructure. Webhook and email integrations let the researcher get notified when long campaigns complete or need attention.

### Steps

- [ ] **10.1** Navigate to the Settings page (`/settings`). Confirm:
  - Settings categories displayed (model routing, integrations, security, etc.)
  - Layout matches screenshot `09-settings-validation-integrations.png`

- [ ] **10.2** Validate configuration. Confirm:
  - Edit or review config in the settings UI
  - Click "Validate" — validation runs against schema
  - Valid config shows success; invalid config shows specific errors
  - `POST /api/v2/config/validate` returns validation result

- [ ] **10.3** Test webhook integration. Confirm:
  - Enter a webhook URL in settings
  - Click "Test" — sends test payload
  - `POST /api/v2/system/webhook/test` returns success/failure
  - If configured, verify the webhook endpoint receives the payload

- [ ] **10.4** Test email integration. Confirm:
  - Enter an email address in settings
  - Click "Test" — sends test email
  - `POST /api/v2/system/email/test` returns success/failure

- [ ] **10.5** Remote safety check. Confirm:
  - If remote access is relevant, `POST /api/v2/system/remote/check` with an origin returns allow/deny

**CLI Cross-Check (Webhooks):**
```bash
openeinstein webhook list
openeinstein webhook add --url https://example.com/hook --events candidate_generated,gate_passed --secret mysecret
openeinstein webhook test --url https://example.com/hook
openeinstein webhook remove --url https://example.com/hook
```

---

## Flow 11: Campaign Builder & Pack Selection

**User Story:** *As a researcher, I want to configure and launch a new campaign visually — choosing a Campaign Pack, setting parameters, and reviewing the schema — without memorizing YAML syntax.*

**PM Intent:** The builder democratizes campaign creation. A grad student who has never written YAML should be able to pick a Campaign Pack, fill in parameters (search space bounds, gate thresholds, model preferences), and start a run. The schema view shows what's configurable and what the defaults are.

### Steps

- [ ] **11.1** Navigate to Builder (`/builder`). Confirm:
  - Pack selector shows available Campaign Packs
  - Schema view displays configurable fields with types and defaults
  - Layout matches screenshot `10-builder-schema.png`

- [ ] **11.2** Select a Campaign Pack. Confirm:
  - Pack details load (description, required capabilities, configurable parameters)
  - `GET /api/v2/packs/{pack_id}/schema` returns schema with field definitions

- [ ] **11.3** Configure and launch. Confirm:
  - Fill in parameters (or accept defaults)
  - Start the run
  - Run appears in runs list with correct pack association
  - Layout matches screenshot `11-builder-run-started.png`

---

## Flow 12: Marketplace — Discovering & Installing Packs

**User Story:** *As a researcher, I want to browse available Campaign Packs and install new ones so I can explore research domains I haven't configured myself.*

**PM Intent:** The marketplace is the extensibility promise made real. Physics specialization lives in packs, not the core platform. A condensed matter physicist should be able to find a phase-classification pack, install it, and run it — without understanding the codebase. Installation should verify integrity (hash pinning, signature verification) transparently.

### Steps

- [ ] **12.1** Navigate to Marketplace (`/marketplace`). Confirm:
  - Available packs listed with name, description, version, install status
  - Layout matches screenshot `12-marketplace-install.png`

- [ ] **12.2** Install a pack from the marketplace. Confirm:
  - Click "Install" on a pack
  - Installation runs with progress feedback
  - `POST /api/v2/packs/install` completes successfully
  - Pack appears in the installed packs list

- [ ] **12.3** Verify installation via CLI:
  ```bash
  openeinstein pack list
  # Newly installed pack should appear
  openeinstein pack verify campaign-packs/<pack-name>/
  # Should show integrity check results (hash match)
  ```

- [ ] **12.4** Test signature verification (security). Confirm:
  - If the pack includes a `pack.sig` and trusted keys are configured, verify that:
    - Valid signatures pass silently
    - Tampered packs are rejected with a clear error message

---

## Flow 13: Layout Customization

**User Story:** *As a researcher who spends hours watching campaigns, I want to customize the dashboard layout to show what matters to me.*

### Steps

- [ ] **13.1** Navigate to Layout settings (`/layout`). Confirm:
  - Layout customization options available (panel arrangement, visible sections, density)
  - Layout matches screenshot `13-layout-customized.png`

- [ ] **13.2** Customize and verify persistence. Confirm:
  - Change layout preferences
  - Refresh the page — customizations persist

---

## Flow 14: Command Palette & Natural Language Navigation

**User Story:** *As a power user, I want a command palette (Cmd+K / Ctrl+K) to quickly navigate, run commands, and control the platform without clicking through menus.*

**PM Intent:** The command palette is for the researcher who lives in keyboard shortcuts. It should feel like VS Code's command palette — fast, fuzzy-matched, and capable of handling natural language. "Start a new run" should work just as well as clicking the builder. This is where the platform reveals its depth without overwhelming new users.

### Steps

- [ ] **14.1** Open the command palette (Cmd+K or Ctrl+K). Confirm:
  - Palette opens as a modal overlay
  - Layout matches screenshot `14-command-palette-open.png`

- [ ] **14.2** Test navigation commands. Confirm:
  - Type "approvals" → navigates to approvals page
  - Type "tools" → navigates to tools page
  - Type "settings" → navigates to settings page

- [ ] **14.3** Test natural language intent resolution. Confirm:
  - Type "start a new run" → resolves to builder or run start action
  - Type "test tool mathematica" → resolves to tool test action
  - Layout matches screenshot `15-command-palette-nl-route.png`
  - `POST /api/v2/intent/command` returns correct action and route

- [ ] **14.4** Verify intent API directly:
  ```bash
  curl -X POST http://localhost:8420/api/v2/intent/command \
    -H "Content-Type: application/json" \
    -d '{"command": "show my approvals"}'
  ```
  Confirm: Returns `action`, `route`, and `message` fields.

---

## Flow 15: Notifications

**User Story:** *As a researcher who may step away while campaigns run, I want notifications for important events (approvals needed, run completed, errors) so I don't miss anything.*

### Steps

- [ ] **15.1** Open the notifications drawer. Confirm:
  - Notification icon/button is visible in the dashboard header
  - Drawer opens showing recent notifications
  - Layout matches screenshot `16-notifications-drawer.png`

- [ ] **15.2** Verify notifications fire for key events. Confirm:
  - Approval requests generate a notification
  - Run completion generates a notification
  - Errors generate a notification with severity indicator

---

## Flow 16: CLI — Campaign Packs & Skills Management

**User Story:** *As a researcher who prefers the terminal, I want full pack and skill management from the CLI with integrity verification, precedence control, and security scanning.*

**PM Intent:** The CLI is the day-1 interface and should remain fully capable even without the dashboard. Every operation the dashboard can perform should have a CLI equivalent. Pack management is a security boundary — hash pinning prevents supply-chain attacks, and the security scanner catches prompt injection in SKILL.md files.

### Steps

- [ ] **16.1** List installed packs:
  ```bash
  openeinstein pack list
  ```
  Confirm: Shows all installed packs with location.

- [ ] **16.2** Install a pack with verification:
  ```bash
  openeinstein pack install campaign-packs/scalar-tensor-lab/
  ```
  Confirm: Pack installs, hash is computed and pinned, security scan runs.

- [ ] **16.3** Verify pack integrity:
  ```bash
  openeinstein pack verify campaign-packs/scalar-tensor-lab/
  ```
  Confirm: Hash matches pinned value — "integrity OK" or equivalent.

- [ ] **16.4** Pin a pack hash:
  ```bash
  openeinstein pack pin campaign-packs/scalar-tensor-lab/
  ```
  Confirm: Hash pinned to metadata store.

- [ ] **16.5** List skills with precedence:
  ```bash
  openeinstein skill list --precedence
  ```
  Confirm: Shows skills with source (workspace/managed/bundled) and version columns. Workspace wins over managed wins over bundled.

- [ ] **16.6** Security scan:
  ```bash
  openeinstein scan
  ```
  Confirm: Scans configs, SKILL.md files, MCP manifests. Reports any risky patterns found (prompt injection, suspicious instructions, base64 payloads).

---

## Flow 17: CLI — Observability (Evals, Traces, Reports)

**User Story:** *As a researcher, I want to run evaluation suites, inspect traces, and generate reports from the CLI so I can verify that the platform is behaving correctly and document my results.*

**PM Intent:** Observability is not optional — it's built in from day 1. Evals verify that skills produce correct outputs, campaigns produce correct end-to-end results, and the persona behaves within defined boundaries. Traces let the researcher audit exactly what happened during a run. Reports are the publishable summary. This is what makes OpenEinstein a research tool rather than a chatbot.

### Steps

- [ ] **17.1** List available eval suites:
  ```bash
  openeinstein eval list
  ```
  Confirm: Shows eval suites from campaign packs and built-in evals.

- [ ] **17.2** Run an eval suite:
  ```bash
  openeinstein eval run <suite_file>
  ```
  Confirm: Evals execute, results printed with pass/fail summary.

- [ ] **17.3** View eval results:
  ```bash
  openeinstein eval results
  ```
  Confirm: Shows results for the most recent eval run.

- [ ] **17.4** List traces for a run:
  ```bash
  openeinstein trace list <run_id>
  ```
  Confirm: Shows spans with timing, tool names, and token counts.

- [ ] **17.5** Export traces:
  ```bash
  openeinstein trace export <run_id> --output traces.json
  ```
  Confirm: OTLP-compatible JSON exported to file.

- [ ] **17.6** Generate a campaign report:
  ```bash
  openeinstein report generate <run_id> --output report.md
  ```
  Confirm: Markdown report generated with candidate summary, failure map, cost breakdown.

- [ ] **17.7** Generate LaTeX report:
  ```bash
  openeinstein report generate <run_id> --output report.md --latex-output report.tex
  ```
  Confirm: Both Markdown and LaTeX versions generated.

- [ ] **17.8** Context report:
  ```bash
  openeinstein context report
  ```
  Confirm: Shows bootstrap context breakdown with per-file token counts and total.

---

## Flow 18: CLI — LaTeX Toolchain

**User Story:** *As a researcher ready to publish, I want to generate a LaTeX skeleton from my campaign results, compile it to PDF, and manage my bibliography — all from the CLI.*

**PM Intent:** LaTeX output is a first-class citizen, not an afterthought. The platform produces derivations, and those derivations need to end up in papers. The LaTeX toolchain should handle the mundane parts (skeleton, bibliography, compilation) so the researcher focuses on the physics narrative.

### Steps

- [ ] **18.1** Generate a LaTeX skeleton:
  ```bash
  openeinstein latex skeleton \
    --title "Modified Gravity Actions: A Systematic Search" \
    --author "Research Group" \
    --abstract "We present a systematic computational search..." \
    --output paper.tex
  ```
  Confirm: `.tex` file generated with proper document structure, placeholder sections.

- [ ] **18.2** Generate bibliography from entries:
  ```bash
  openeinstein latex bibgen entries.json --output references.bib
  ```
  Confirm: `.bib` file generated with proper BibTeX entries.

- [ ] **18.3** Compile LaTeX to PDF:
  ```bash
  openeinstein latex build paper.tex
  ```
  Confirm: PDF generated (requires latexmk installed). Clean exit code.

- [ ] **18.4** Clean auxiliary files:
  ```bash
  openeinstein latex clean paper.tex
  ```
  Confirm: Auxiliary files (.aux, .log, .bbl, etc.) removed. Source .tex preserved.

---

## Flow 19: Concurrency & Lane Control

**User Story:** *As a researcher running a campaign with independent phases (literature search + candidate generation), I want them to run concurrently so my campaign finishes faster — with configurable limits so I don't overwhelm my machine.*

**PM Intent:** Concurrency is a throughput multiplier. A campaign with 4 independent literature queries and 8 candidate generation tasks shouldn't serialize them. But the researcher needs control — their laptop might not handle 16 concurrent Mathematica kernels. Lane caps are the safety valve. Queue modes (collect/followup/steer) let the researcher interact with a running campaign without stopping it.

### Steps

- [ ] **19.1** Start a campaign with parallel lanes:
  ```bash
  openeinstein run start campaign.yaml --parallel-lanes 4
  ```
  Confirm: Run starts with lane concurrency configured.

- [ ] **19.2** Verify lane behavior in events. Confirm:
  - Independent phases (e.g., literature + generating) run concurrently
  - Lane caps are respected (no more than N concurrent tasks per lane)
  - Events show interleaved progress from multiple lanes

- [ ] **19.3** Verify lane config:
  ```bash
  cat configs/lanes.yaml
  ```
  Confirm: Lane definitions present with names and max_concurrent values.

---

## Flow 20: Security — Sandbox & Budget Enforcement

**User Story:** *As a researcher, I want to know that tool calls are sandboxed (no unexpected network access, no filesystem writes outside my workspace) and that my LLM budget is enforced — so a runaway campaign doesn't cost me $500.*

**PM Intent:** Security is not a feature flag — it's an architectural invariant. The gateway enforces policy before every tool call, not the LLM. Budget enforcement is a hard cap, not a warning. Tool sandbox profiles (minimal/research/full) give the researcher control over what each tool can do. The circuit breaker prevents cascading failures when a provider goes down.

### Steps

- [ ] **20.1** Verify tool sandbox profiles exist:
  ```bash
  cat configs/tool-profiles.yaml
  ```
  Confirm: Presets defined (minimal, research, full) with clear allow/deny rules.

- [ ] **20.2** Sandbox explain command:
  ```bash
  openeinstein sandbox explain "tool X was blocked"
  ```
  Confirm: Explains which policy rule blocked the tool call and why.

- [ ] **20.3** Verify budget enforcement. Confirm:
  - Gateway-level budget limits are configured in policy
  - When a budget is exceeded, the run stops with a clear error (not a silent failure)
  - Budget warning hook fires before the hard cap is hit

---

## Flow 21: Fork-from-Event & Replay

**User Story:** *As a researcher reviewing a completed campaign, I want to fork a new run from a specific point in a previous run — replaying up to event N and then diverging with different parameters.*

**PM Intent:** Research is exploratory. Sometimes you realize at event 47 that the gate threshold was wrong. Rather than re-running the entire campaign, fork from event 47 with new thresholds. This turns the platform from a one-shot runner into an iterative research tool.

### Steps

- [ ] **21.1** Fork a run from a specific event:
  ```bash
  curl -X POST http://localhost:8420/api/v2/runs/<run_id>/fork \
    -H "Content-Type: application/json" \
    -d '{"event_index": 47}'
  ```
  Confirm: New run created, starting from the state at event 47.

- [ ] **21.2** Verify the forked run in the dashboard. Confirm:
  - New run appears in the runs list
  - It references the parent run
  - Event stream begins from the fork point, not from zero

---

## Flow 22: Cost Tracking

**User Story:** *As a researcher on a budget, I want to see how much each campaign run cost (LLM tokens, API calls) so I can optimize my model routing and budget allocation.*

### Steps

- [ ] **22.1** View cost data for a run:
  ```bash
  curl http://localhost:8420/api/v2/runs/<run_id>/cost
  ```
  Confirm: Returns cost breakdown (tokens used per model role, estimated USD, tool call counts).

- [ ] **22.2** Verify cost data in dashboard. Confirm:
  - Run detail view shows cost information
  - Cost breakdown is per-role (reasoning, generation, fast, embeddings)

---

## Flow 23: End-to-End Campaign Lifecycle (Integration)

**User Story:** *As a researcher, I want to run a complete campaign from start to finish — configure, execute, monitor, review results, export — and verify that every piece of the platform works together.*

**PM Intent:** This is the "does it actually work" test. A campaign should flow naturally from config to results. The researcher's journey: install pack, start run, watch events, handle approvals, review artifacts, compare runs, export report. If any link in this chain breaks, the platform fails its purpose.

### Steps

- [ ] **23.1** Initialize workspace:
  ```bash
  openeinstein init
  ```

- [ ] **23.2** Install a Campaign Pack:
  ```bash
  openeinstein pack install campaign-packs/scalar-tensor-lab/
  ```

- [ ] **23.3** Start the campaign:
  ```bash
  openeinstein run start campaign-packs/scalar-tensor-lab/campaign.yaml --parallel-lanes 2
  ```

- [ ] **23.4** Monitor in dashboard — events stream in real time.

- [ ] **23.5** Handle any approval requests (grant in CLI or dashboard).

- [ ] **23.6** Wait for completion:
  ```bash
  openeinstein run wait <run_id> --timeout 300
  ```

- [ ] **23.7** Review results:
  ```bash
  openeinstein results <run_id>
  ```

- [ ] **23.8** Browse artifacts in dashboard.

- [ ] **23.9** Generate report:
  ```bash
  openeinstein report generate <run_id> --output report.md --latex-output report.tex
  ```

- [ ] **23.10** Tag and compare with previous runs in dashboard.

- [ ] **23.11** Export run:
  ```bash
  curl -X POST http://localhost:8420/api/v2/runs/<run_id>/export
  ```

- [ ] **23.12** Final verification:
  - All artifacts downloadable
  - Traces exportable
  - Eval results available
  - No unhandled errors in terminal logs
  - Dashboard shows correct final state

---

## Appendix A: API Health Checklist

Quick smoke test of all API endpoints. Run with curl or from the browser console.

| Endpoint | Method | Expected |
|----------|--------|----------|
| `/api/v2/health` | GET | 200 OK |
| `/api/v2/version` | GET | Version object |
| `/api/v2/system` | GET | System config |
| `/api/v2/runs` | GET | Run list |
| `/api/v2/tools` | GET | Tool list |
| `/api/v2/approvals` | GET | Approvals list |
| `/api/v2/config` | GET | Dashboard config |
| `/api/v2/packs` | GET | Pack list |
| `/api/v2/packs/marketplace` | GET | Marketplace list |
| `/api/v2/config/example` | GET | Example YAML |

## Appendix B: Screenshot Reference

| Screenshot | Flow |
|-----------|------|
| `01-runs-overview.png` | Flow 2: Runs dashboard |
| `02-runs-control-resume.png` | Flow 5: Pause/resume |
| `03-approvals-pending.png` | Flow 6: Pending approvals |
| `04-approvals-cleared.png` | Flow 6: Approved |
| `05-artifacts-before-export.png` | Flow 7: Artifacts list |
| `06-artifacts-exported-preview.png` | Flow 7: Export preview |
| `07-compare-and-tag.png` | Flow 8: Run comparison |
| `08-tools-page.png` | Flow 9: Tools status |
| `09-settings-validation-integrations.png` | Flow 10: Settings |
| `10-builder-schema.png` | Flow 11: Campaign builder |
| `11-builder-run-started.png` | Flow 11: Run started |
| `12-marketplace-install.png` | Flow 12: Marketplace |
| `13-layout-customized.png` | Flow 13: Layout |
| `14-command-palette-open.png` | Flow 14: Command palette |
| `15-command-palette-nl-route.png` | Flow 14: NL intent |
| `16-notifications-drawer.png` | Flow 15: Notifications |

## Appendix C: CLI Command Quick Reference

```bash
# Lifecycle
openeinstein init
openeinstein dashboard [--port 8420]
openeinstein run start <campaign.yaml> [--parallel-lanes N]
openeinstein run status [run_id]
openeinstein run events [run_id]
openeinstein run stop <run_id>
openeinstein run resume <run_id>
openeinstein run wait [run_id] [--timeout N]

# Results & Export
openeinstein results [run_id]
openeinstein export [run_id] [--output PATH]
openeinstein report generate [run_id] [--output PATH] [--latex-output PATH]

# Packs & Skills
openeinstein pack list
openeinstein pack install <source> [--skip-verify]
openeinstein pack verify <path>
openeinstein pack pin <path>
openeinstein skill list [--precedence]

# Security
openeinstein approvals list|grant|revoke|reset
openeinstein scan [paths...]
openeinstein sandbox explain [message]

# Observability
openeinstein eval list|run|results
openeinstein trace list|export [run_id]
openeinstein context report

# LaTeX
openeinstein latex skeleton|build|compile|clean|bibgen

# Webhooks
openeinstein webhook list|add|remove|test

# Diagnostics
openeinstein version
openeinstein config [--validate]
openeinstein campaign clean [--run-id ID] --yes
```
