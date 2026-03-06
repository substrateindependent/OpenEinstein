# OpenEinstein Development Plan — OpenClaw Architecture Integration

> Based on the [OpenClaw Applicability Assessment](../research/OpenClaw-Applicability-Assessment.docx). This plan covers the ADOPT and ADAPT recommendations rated medium-to-high priority, organized into seven sequential phases.

---

## Sequencing Rationale

Phases are ordered by dependency and value:

- **Phase 1 (Concurrency)** comes first because it unblocks parallel campaign execution, a prerequisite for throughput gains in later phases.
- **Phase 2 (Skill Hardening)** follows because the security patterns it introduces (hash pinning, scanning) are reused by Phase 4.
- **Phase 3 (Memory/Compaction)** builds on the orchestrator changes from Phase 1.
- **Phase 4 (Security)** reuses primitives from Phase 2 (MetadataPinStore, SecurityScanner).
- **Phase 5 (Hooks/Webhooks)** extends the hook registry touched in Phases 1 and 3.
- **Phase 6 (Harness Abstraction)** is a refactoring phase that benefits from all prior changes being stable.
- **Phase 7 (Gateway Protocol)** is last because it is the most isolated change.

---

## Phase Overview

| Phase | Epic | Key Deliverable | Depends On |
|-------|------|-----------------|------------|
| 1 | Concurrency & Campaign Throughput | Lane-aware executor | None |
| 2 | Skill & Pack Ecosystem Hardening | Versioned pack installer | None |
| 3 | Memory, Compaction & Context Management | Tiered compaction engine | Phase 1 |
| 4 | Security & Supply-Chain Hardening | Pack signing + tool profiles | Phase 2 |
| 5 | Hook System Extension & Outbound Webhooks | Outbound webhooks | Phases 1, 3 |
| 6 | Runtime Harness Abstraction & Session Isolation | Harness interface + sandbox | All prior |
| 7 | Gateway Protocol Hardening | Idempotency + client ID | Phase 4 |

---

## Phase 1: Concurrency & Campaign Throughput

**Summary:** Add lane-aware concurrency queuing to the campaign executor so multiple campaign steps and parallel runs no longer bottleneck on a single thread pool.

**Objective:** Enable the campaign executor to run multiple step phases and parallel sub-runs concurrently, with configurable per-lane limits and queue modes.

### Deliverables

- Lane registry with configurable concurrency caps per lane (main, subagent, literature, gating)
- Queue mode support: `collect` (default), `followup`, and `steer` for UI-initiated mid-run intervention
- Per-lane semaphore enforcement in `CampaignExecutor._execute_loop`
- Updated campaign state machine to handle concurrent step interleaving
- CLI flag `--parallel-lanes N` for operator control
- Integration tests covering lane isolation, cap enforcement, and queue mode behavior

### Tasks

| File | Action | Description |
|------|--------|-------------|
| `src/openeinstein/campaigns/lanes.py` | Create | New module: `LaneRegistry` class with named lanes, configurable concurrency semaphores, and acquire/release methods. Pydantic model `LaneConfig` with fields: `name`, `max_concurrent` (default 4), `queue_mode` (enum: collect\|followup\|steer). |
| `src/openeinstein/campaigns/executor.py` | Modify | Replace single-threaded `_execute_loop` with lane-aware dispatch. Each step phase maps to a lane (planning/verifying → main, generating/gating → generation, literature → literature). `_spawn_worker` acquires lane semaphore before executing, releases after. Add `desired_state` check between lane acquire and step execution for interrupt responsiveness. |
| `src/openeinstein/campaigns/state.py` | Modify | Add `ConcurrentStepTracker` to `CampaignStateMachine` that tracks which lanes have active steps. Add `allowed_concurrent_transitions` set. Add `lane_status` property returning per-lane active/queued counts. |
| `src/openeinstein/campaigns/queue_modes.py` | Create | `QueueMode` enum and `QueueModeHandler` class. `collect`: coalesce queued messages into single follow-up. `followup`: enqueue for next turn. `steer`: cancel pending tool calls at next boundary and inject new instruction. Wire into executor via new `_handle_mid_run_message` method. |
| `src/openeinstein/cli/commands.py` | Modify | Add `--parallel-lanes` option to campaign run command. Pass through to `RuntimeLimits`. Add lane status display to `campaign status` command. |
| `configs/lanes.yaml` | Create | Default lane configuration file: main(4), subagent(8), literature(2), gating(2). Loaded by `CampaignExecutor.__init__`. |
| `tests/test_lanes.py` | Create | Unit tests: lane semaphore enforcement, concurrent step isolation, queue mode coalescing, steer interruption at tool boundary, cap overflow queuing. |
| `tests/integration/test_concurrent_campaign.py` | Create | Integration test: run a campaign with parallel generating+literature steps, verify both complete, verify lane caps are respected, verify events are ordered correctly in JSONL. |

### Acceptance Criteria

A campaign with independent steps (e.g., literature + generating) runs them concurrently up to lane caps. Queue modes correctly coalesce or inject mid-run. `pytest` passes with no regressions.

---

## Phase 2: Skill & Pack Ecosystem Hardening

**Summary:** Add semantic versioning, precedence rules, and installation verification to the skill/campaign-pack ecosystem, laying groundwork for a future marketplace.

**Objective:** Ensure campaign packs and skills are versioned, integrity-verified on install, and loaded with clear precedence (workspace > user > bundled), preventing supply-chain attacks and version conflicts.

### Deliverables

- Semantic version field in SKILL.md frontmatter and campaign pack manifests
- Precedence-aware skill discovery (workspace > managed > bundled)
- SHA-256 content hash pinning on pack install via `MetadataPinStore`
- Pack manifest schema with required fields: name, version, author, license, hash
- CLI commands: `pack verify`, `pack pin`, `skill list --precedence`
- `SecurityScanner` extended with `SKILL_MD_INJECTION` rule for instruction-level scanning
- Unit and integration tests for versioning, precedence, and integrity verification

### Tasks

| File | Action | Description |
|------|--------|-------------|
| `src/openeinstein/skills/models.py` | Modify | Add `version: str \| None` field to `SkillMetadata`. Add `SkillSource` enum (bundled, managed, workspace). Add `precedence_rank` computed from source. Add `PackManifest` Pydantic model with fields: name, version, author, license, sha256, dependencies list, min_platform_version. |
| `src/openeinstein/skills/registry.py` | Modify | Refactor `discover_skills` to tag each skill with its `SkillSource` based on which root it came from. Implement precedence: if same skill name exists in multiple roots, workspace wins over managed wins over bundled. Parse YAML frontmatter from SKILL.md for version extraction. Add `list_with_precedence()` method returning skills with source and version. |
| `src/openeinstein/skills/versioning.py` | Create | Semantic version comparison utilities: `parse_version`, `is_compatible`, `version_satisfies_constraint`. Support ranges like `>=1.2.0,<2.0.0`. Used by registry and pack installer. |
| `src/openeinstein/skills/installer.py` | Create | `PackInstaller` class: download/copy pack to managed directory, validate manifest schema, compute SHA-256 of pack contents, pin hash via `MetadataPinStore`, run `SecurityScanner` on SKILL.md files, report findings before completing install. Method: `install(source_path, verify=True) -> InstallResult`. |
| `src/openeinstein/security/core.py` | Modify | Add `SKILL_MD_INJECTION` rule to `SecurityScanner._RULES`: detect patterns like hidden instructions, base64-encoded payloads, and prompt injection attempts in SKILL.md files. Add `MANIFEST_MISMATCH` rule checking declared vs actual file hashes. |
| `src/openeinstein/cli/commands.py` | Modify | Add `pack verify <path>` command that re-computes hashes and compares against pinned values. Add `pack pin <path>` to manually pin a pack. Add `skill list --precedence` flag showing source and version columns. Add `pack install <source>` with `--skip-verify` flag. |
| `campaign-packs/_marketplace/manifest-schema.json` | Create | JSON Schema for pack manifests. Required fields: name, version (semver), author, license, sha256. Optional: description, dependencies, min_platform_version, tags. |
| `tests/test_skill_versioning.py` | Create | Tests for version parsing, comparison, range satisfaction. Tests for precedence ordering. Tests for frontmatter extraction. |
| `tests/test_pack_installer.py` | Create | Tests: install valid pack, reject tampered pack (hash mismatch), reject pack with SKILL_MD_INJECTION finding, verify pinning persists across reinstall. |
| `tests/integration/test_skill_precedence.py` | Create | Integration test: create conflicting skills in workspace and bundled roots, verify workspace version wins. Verify version constraints are checked during context assembly. |

### Acceptance Criteria

Packs install with hash verification. Tampered packs are rejected. Skill precedence follows workspace > managed > bundled. `SecurityScanner` catches injection patterns in SKILL.md. CLI commands work end-to-end.

---

## Phase 3: Memory, Compaction & Context Management

**Summary:** Replace the basic `compact_with_invariants` truncation with a structured, tiered compaction system that preserves critical context across long-running campaigns.

**Objective:** Implement a multi-tier compaction strategy with pinned context blocks, configurable retention policies, and silent memory flush capability for long-running campaign sessions.

**Depends on:** Phase 1 (orchestrator changes).

### Deliverables

- `CompactionEngine` with tiered summarization (pin > recent > summary > discard)
- Pinnable context blocks that survive all compaction passes
- Per-content-type retention policies (safety tokens: always retain; reasoning chains: summarize; tool outputs: discard after N steps)
- Silent memory flush mechanism for pre-compaction durable note persistence
- Token budget tracking integrated with `ModelRouter` usage recording
- Compaction event logging in JSONL event streams

### Tasks

| File | Action | Description |
|------|--------|-------------|
| `src/openeinstein/agents/compaction.py` | Create | `CompactionEngine` class with methods: `compact(context, budget) -> CompactedContext`. Implements 4-tier strategy: (1) pinned blocks always retained, (2) recent N turns retained verbatim, (3) older turns summarized via fast model role, (4) ancient turns discarded. `ContentBlock` Pydantic model with fields: content, block_type (pinned\|recent\|summary\|ephemeral), created_at, token_count. `RetentionPolicy` model with per-type rules. |
| `src/openeinstein/agents/context_pins.py` | Create | `ContextPinRegistry` class: `pin(block_id, content, reason)`, `unpin(block_id)`, `list_pins()`. Pinned blocks are persisted to SQLite and injected at top of every compacted context. Campaign safety invariants are auto-pinned at run start. |
| `src/openeinstein/agents/memory_flush.py` | Create | `MemoryFlushManager`: before compaction, invokes a fast-model turn with a structured prompt asking the model to extract durable notes from context. Notes are written to campaign artifacts. Uses `NO_REPLY` pattern (result persisted but not delivered to UI). Method: `flush_before_compaction(run_id, context) -> list[DurableNote]`. |
| `src/openeinstein/agents/orchestrator.py` | Modify | Replace `compact_with_invariants` with `CompactionEngine.compact()`. Wire `ContextPinRegistry` into orchestrator init. Auto-pin invariants list at construction. Update `execute()` to check token budget before each task dispatch and trigger compaction if over threshold. |
| `src/openeinstein/campaigns/executor.py` | Modify | Integrate `CompactionEngine` into step pipeline. After each step completion, check cumulative token usage against budget. If over 70% threshold, trigger memory flush then compaction. Log `compaction_triggered` event to JSONL stream with before/after token counts. |
| `src/openeinstein/persistence/db.py` | Modify | Add `context_pins` table (pin_id, run_id, block_type, content, reason, created_at). Add `durable_notes` table (note_id, run_id, step_id, content, created_at). Add CRUD methods: `add_pin`, `get_pins`, `remove_pin`, `add_durable_note`, `get_durable_notes`. |
| `configs/compaction.yaml` | Create | Default compaction config: `recent_turns_keep=5`, `summary_model_role=fast`, `pin_safety_tokens=true`, `flush_before_compact=true`, `budget_trigger_pct=70`, retention rules per block type. |
| `tests/test_compaction.py` | Create | Unit tests: 4-tier compaction produces correct output, pinned blocks survive compaction, token budget enforcement triggers compaction, retention policies applied per type. Edge cases: empty context, all-pinned context, budget smaller than pins. |
| `tests/test_memory_flush.py` | Create | Tests: flush extracts notes, notes are persisted, flush failure doesn't block compaction, NO_REPLY pattern suppresses delivery. |

### Acceptance Criteria

Long campaigns (20+ steps) maintain coherent context without token overflow. Pinned safety invariants are present in every compacted context. Memory flush captures durable notes before compaction. Token budgets are enforced.

---

## Phase 4: Security & Supply-Chain Hardening

**Summary:** Extend security infrastructure with pack signing, token budget enforcement at the gateway level, and per-tool sandbox profiles.

**Objective:** Treat campaign packs as executable code with provenance verification, enforce hard token/cost budgets in the gateway (not just campaign-level), and add per-tool allow/deny profiles.

**Depends on:** Phase 2 (MetadataPinStore, SecurityScanner patterns).

### Deliverables

- Ed25519 pack signing and verification workflow
- Gateway-level token budget enforcement as a policy invariant
- Per-tool `ToolSandboxProfile` with allow/deny rules loaded from YAML
- Tool profile presets (minimal, research, full) with layered override
- Token exhaustion circuit breaker in `ModelRouter`
- Extended `SecurityScanner` with pack provenance rules

### Tasks

| File | Action | Description |
|------|--------|-------------|
| `src/openeinstein/security/signing.py` | Create | `PackSigner` class: `generate_keypair() -> (public, private)` using Ed25519, `sign_pack(pack_path, private_key) -> signature file`, `verify_pack(pack_path, public_key, signature) -> bool`. Signature covers SHA-256 of all pack files concatenated in sorted order. Store public keys in `configs/trusted-keys/`. |
| `src/openeinstein/security/core.py` | Modify | Add `ToolSandboxProfile` Pydantic model with fields: tool_name_pattern (glob), allow_network, allow_fs_write, allow_shell, max_tokens_per_call, max_calls_per_run. Add `ToolProfileRegistry` that loads profiles from YAML, supports preset inheritance (minimal extends nothing, research extends minimal, full allows all). Add deny_wins merge logic for layered profiles. |
| `src/openeinstein/gateway/policy.py` | Modify | Add gateway-level budget fields to `PolicyInvariants`: `max_total_tokens_per_session` (int), `max_total_cost_per_session_usd` (float), `circuit_breaker_consecutive_failures` (int, default 5). `PolicyEngine.enforce_budget(session_usage)` raises `PolicyViolationError` on breach. |
| `src/openeinstein/routing/router.py` | Modify | Add `CircuitBreaker` class: tracks consecutive failures per role. After N consecutive failures (configurable, default 5), open the breaker and refuse requests for a cooldown period. Reset on success. Wire into `run_with_fallback`: check breaker state before attempting call. |
| `src/openeinstein/gateway/hooks.py` | Modify | Add `ToolSandboxHook` that checks tool calls against `ToolProfileRegistry` before execution. If tool violates its sandbox profile (e.g., network call when allow_network=false), return `HookResponse(allow=False)`. Register at `before_tool_call` hook point. |
| `configs/tool-profiles.yaml` | Create | Preset definitions: minimal (no network, no shell, no fs write), research (allow network for literature tools, no shell), full (all allowed). Per-tool overrides section. |
| `configs/trusted-keys/` | Create | Directory for Ed25519 public keys of trusted pack authors. Ship with project maintainer key. |
| `tests/test_signing.py` | Create | Tests: generate keypair, sign pack, verify valid signature, reject tampered pack, reject wrong key. |
| `tests/test_tool_profiles.py` | Create | Tests: profile loading, preset inheritance, deny_wins merge, sandbox hook blocks disallowed tool, sandbox hook allows permitted tool. |
| `tests/test_circuit_breaker.py` | Create | Tests: breaker opens after N failures, breaker rejects during cooldown, breaker resets on success, breaker integrates with `run_with_fallback`. |
| `tests/test_gateway_budget.py` | Create | Tests: gateway enforces session token limit, gateway enforces session cost limit, budget violation raises `PolicyViolationError`, budget tracking accumulates across runs. |

### Acceptance Criteria

Signed packs verify correctly; unsigned or tampered packs are rejected. Gateway enforces hard token/cost budgets. Tool sandbox profiles block disallowed operations. Circuit breaker prevents runaway failures.

---

## Phase 5: Hook System Extension & Outbound Webhooks

**Summary:** Extend the hook system with additional lifecycle events and add outbound webhook support so external systems can subscribe to campaign events.

**Objective:** Complete the event-driven automation layer with richer hook points covering the full campaign lifecycle, plus HTTP-based outbound webhooks for integration with external tooling.

**Depends on:** Phases 1 and 3 (executor and compaction hook integration points).

### Deliverables

- New hook points: `before_compaction`, `after_compaction`, `candidate_generated`, `gate_passed`, `gate_failed`, `budget_warning`
- Outbound webhook dispatcher with configurable URL targets, retry logic, and HMAC signing
- Webhook registration via YAML config and CLI
- Event filtering: webhooks can subscribe to specific event types

### Tasks

| File | Action | Description |
|------|--------|-------------|
| `src/openeinstein/gateway/hooks.py` | Modify | Add 6 new `HookPoint` literals: `before_compaction`, `after_compaction`, `candidate_generated`, `gate_passed`, `gate_failed`, `budget_warning`. Initialize empty lists in `HookRegistry.__init__`. Integrate dispatch calls into `CampaignExecutor` at appropriate points. |
| `src/openeinstein/gateway/webhooks.py` | Create | `WebhookDispatcher` class: `register(url, events, secret)`, `dispatch(event_type, payload)`. HTTP POST with JSON body, HMAC-SHA256 signature header (`X-OpenEinstein-Signature`), configurable retry (3 attempts, exponential backoff). `WebhookConfig` Pydantic model. Async dispatch via threading to avoid blocking the campaign loop. |
| `src/openeinstein/gateway/hooks.py` | Modify | Add `WebhookBridgeHook` that wraps `WebhookDispatcher` as a Hook. On dispatch, filters events by the webhook's subscribed event list and forwards matching events. Register bridge hooks from webhook config. |
| `configs/webhooks.yaml` | Create | Webhook registration config: list of `{url, events: [...], secret, enabled, retry_count}`. Loaded at gateway startup. |
| `src/openeinstein/cli/commands.py` | Modify | Add `webhook add/remove/list/test` CLI commands. `webhook test` sends a test payload to the URL and reports success/failure. |
| `tests/test_webhooks.py` | Create | Tests: webhook dispatch sends correct payload, HMAC signature is valid, retry on failure, event filtering respects subscription list, webhook bridge integrates with `HookRegistry`. |

### Acceptance Criteria

Webhooks fire on campaign events with valid HMAC signatures. Event filtering works correctly. Retries handle transient failures. New hook points fire at correct lifecycle moments.

---

## Phase 6: Runtime Harness Abstraction & Session Isolation

**Summary:** Extract a runtime harness interface from the campaign executor and formalize per-run session isolation as a security boundary.

**Objective:** Decouple the agent execution substrate from the campaign control plane, and ensure each campaign run has its own isolated filesystem scope, token budget, and approval context.

**Depends on:** All prior phases (this is a refactoring phase that benefits from stability).

### Deliverables

- `RuntimeHarness` protocol with methods: `initialize`, `execute_step`, `get_state`, `cleanup`
- `PydanticAIHarness`: default implementation wrapping current orchestrator
- `SessionSandbox`: per-run isolated working directory with cleanup lifecycle
- Per-run approval context isolation (approvals granted in one run don't leak to another)
- Harness selection via campaign pack config

### Tasks

| File | Action | Description |
|------|--------|-------------|
| `src/openeinstein/agents/harness.py` | Create | `RuntimeHarness` Protocol with methods: `initialize(run_config) -> None`, `execute_step(phase, context) -> StepResult`, `get_state() -> HarnessState`, `cleanup() -> None`. `PydanticAIHarness` class implementing the protocol by wrapping `AgentOrchestrator`. `HarnessFactory`: `create(harness_type, config) -> RuntimeHarness`. |
| `src/openeinstein/security/sandbox.py` | Create | `SessionSandbox` class: creates isolated temp directory per run under `.openeinstein/sandboxes/{run_id}/`. Provides scoped paths for artifacts, working files, and tool outputs. `cleanup()` removes directory. Context manager support. Enforced filesystem boundary: tool calls that reference paths outside sandbox are blocked. |
| `src/openeinstein/security/core.py` | Modify | Add `ScopedApprovalsStore` that wraps `ApprovalsStore` with run_id scoping. Approvals granted in one run are stored under run_id namespace and don't leak to other runs. `reset_run(run_id)` clears only that run's approvals. |
| `src/openeinstein/campaigns/executor.py` | Modify | Replace direct orchestrator usage with `RuntimeHarness` interface. Create `SessionSandbox` at run start, inject into harness. Use `ScopedApprovalsStore` per run. Cleanup sandbox on run completion/failure. |
| `src/openeinstein/campaigns/config.py` | Modify | Add `harness_type` field to `CampaignDefinition` (default: `'pydantic-ai'`). Add `sandbox_mode` field (default: `'isolated'`). Validate against registered harness types. |
| `tests/test_harness.py` | Create | Tests: `PydanticAIHarness` delegates to orchestrator correctly, `HarnessFactory` creates correct type, harness lifecycle (init/execute/cleanup) works end-to-end. |
| `tests/test_session_sandbox.py` | Create | Tests: sandbox creates isolated directory, path resolution stays within sandbox, cleanup removes directory, scoped approvals don't leak between runs. |

### Acceptance Criteria

Campaign executor uses harness interface. Each run gets an isolated sandbox. Approvals don't leak between runs. Harness type is selectable per campaign pack.

---

## Phase 7: Gateway Protocol Hardening

**Summary:** Add idempotency keys and client identity tracking to the gateway protocol for retry safety and multi-client support.

**Objective:** Ensure all side-effecting gateway operations are idempotent under retries, and track client identity for audit and multi-client coordination.

**Depends on:** Phase 4 (gateway policy infrastructure).

### Deliverables

- Idempotency key field on all mutating `WSClientMessage` types
- Server-side idempotency cache with configurable TTL
- Client identity tracking (`device_id`, `client_version`) on connect
- Duplicate run prevention via idempotency key dedup

### Tasks

| File | Action | Description |
|------|--------|-------------|
| `src/openeinstein/gateway/ws/protocol.py` | Modify | Add `idempotency_key: str \| None` field to `WSClientMessage`. Add `client_id: str \| None` and `client_version: str \| None` fields to connect message type. Validate idempotency key format (UUID or similar). |
| `src/openeinstein/gateway/idempotency.py` | Create | `IdempotencyCache` class: `check_and_store(key, result) -> CachedResult \| None`. In-memory dict with TTL-based expiry (default 5 minutes). Thread-safe. Returns cached result if key already processed, None if new. |
| `src/openeinstein/gateway/ws/handler.py` | Modify | Integrate `IdempotencyCache`: before processing `run_command` or `approval_decision`, check cache. If cached, return cached response. After processing, store result in cache. Track client identity from connect frame, include in audit log entries. |
| `tests/test_idempotency.py` | Create | Tests: duplicate key returns cached result, TTL expiry allows reprocessing, concurrent requests with same key are deduped, different keys are independent. |

### Acceptance Criteria

Retried run commands with same idempotency key don't create duplicate runs. Client identity appears in audit logs. TTL expiry works correctly.

---

## Testing Strategy

Each phase includes its own unit and integration tests as specified in the task breakdowns. The following cross-cutting practices apply:

**Regression gate:** Run the full `pytest` suite after completing each phase. No phase is considered complete until all existing tests pass alongside new tests.

**Integration coverage:** Each phase includes at least one integration test that exercises the cross-subsystem wiring introduced by that phase (e.g., lane-aware executor + state machine in Phase 1, pack installer + security scanner in Phase 2).

**Eval fixtures:** Phases that change agent behavior (1, 3, 6) should add or update eval fixtures in `evals/` to catch persona and safety regressions.

**Performance baselines:** Phase 1 (concurrency) and Phase 3 (compaction) should establish timing baselines for campaign execution and context assembly, tracked in CI.

---

## Deferred Backlog (MONITOR items)

The following OpenClaw patterns were rated MONITOR in the applicability assessment. They are not included in this plan but may be revisited in future cycles:

**Workspace Bootstrapping (OpenClaw §10):** File-based persona/memory/identity model. Interesting for campaign pack self-description but low priority for a research platform where identity is defined by the campaign pack itself.

**Proactivity & Scheduling (OpenClaw §12):** Heartbeat and cron-triggered campaigns. Useful for nightly literature scans or periodic re-evaluation. Could be implemented as a lightweight scheduler on top of the hook system from Phase 5.

**Deterministic Workflows / OpenProse (OpenClaw §17):** YAML-based workflow definitions with explicit control flow. Could complement the campaign state machine for simpler, linear research workflows. Worth exploring once the harness abstraction (Phase 6) is stable.

**Channel Adapters (OpenClaw §5):** Skipped. Multi-channel messaging is not relevant to a research platform.
