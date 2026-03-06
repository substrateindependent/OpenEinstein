# EPIC-OC: OpenClaw Architecture Integration

**Status:** Complete
**Started:** 2026-03-04
**Completed:** 2026-03-04
**Source:** `docs/build-plans/OpenClaw-Integration-DevPlan.md`

## Overview

Seven sequential phases of architectural improvements inspired by the OpenClaw Applicability Assessment, covering concurrency, skill hardening, compaction, security, webhooks, harness abstraction, and gateway protocol hardening. Together they transform OpenEinstein from a single-threaded, trust-on-install research platform into a concurrent, auditable, multi-client system.

## Phases

| Phase | Name | Status | Stories |
|-------|------|--------|---------|
| 1 | Concurrency & Campaign Throughput | Complete | 1.1-1.5 |
| 2 | Skill & Pack Ecosystem Hardening | Complete | 2.1-2.4 |
| 3 | Memory, Compaction & Context Management | Complete | 3.1-3.4 |
| 4 | Security & Supply-Chain Hardening | Complete | 4.1-4.5 |
| 5 | Hook System Extension & Outbound Webhooks | Complete | 5.1-5.3 |
| 6 | Runtime Harness Abstraction & Session Isolation | Complete | 6.1-6.3 |
| 7 | Gateway Protocol Hardening | Complete | 7.1-7.2 |

## Key Decisions

- **Phase ordering:** Strict sequential (1 through 7). Each phase fully completed before the next.
- **Cryptographic library:** `cryptography` (OpenSSL-based) for Ed25519 pack signing in Phase 4.
- **Concurrency primitives:** `threading.Semaphore` (not asyncio) since `CampaignExecutor` already uses threading.
- **Backward compatibility:** All modifications to existing classes accept new parameters as optional with `None` defaults, preserving existing behavior.
- **Compaction strategy:** 4-tier (pinned > recent > summary > discard) with configurable retention policies.
- **Sandbox isolation:** Per-run temp directory under `.openeinstein/sandboxes/{run_id}/` with path boundary enforcement.
- **Hook system:** 11 total hook points (5 original + 6 new), all initialized in `HookRegistry.__init__`.
- **Webhook signing:** HMAC-SHA256 with per-webhook secrets, sent as `X-OpenEinstein-Signature` header.

## Files Created (12 source + 5 config + 26 test)

### Source Files

| File | LOC | Phase | Purpose |
|------|-----|-------|---------|
| `src/openeinstein/campaigns/lanes.py` | 140 | 1 | Lane registry with configurable concurrency semaphores |
| `src/openeinstein/campaigns/queue_modes.py` | 98 | 1 | Queue mode handlers (collect/followup/steer) |
| `src/openeinstein/skills/versioning.py` | 73 | 2 | Semantic versioning utilities |
| `src/openeinstein/skills/installer.py` | 141 | 2 | Pack installer with hash pinning and security scanning |
| `src/openeinstein/agents/compaction.py` | 224 | 3 | Tiered compaction engine with content blocks |
| `src/openeinstein/agents/context_pins.py` | 52 | 3 | Context pin registry with SQLite persistence |
| `src/openeinstein/agents/memory_flush.py` | 94 | 3 | Pre-compaction memory flush manager |
| `src/openeinstein/agents/harness.py` | 149 | 6 | Runtime harness protocol and PydanticAI implementation |
| `src/openeinstein/security/signing.py` | 93 | 4 | Ed25519 pack signing and verification |
| `src/openeinstein/security/sandbox.py` | 110 | 6 | Session sandbox with scoped approvals |
| `src/openeinstein/gateway/webhooks.py` | 168 | 5 | Outbound webhook dispatcher with HMAC and retry |
| `src/openeinstein/gateway/idempotency.py` | 94 | 7 | Idempotency cache for WS deduplication |

### Configuration Files

| File | Phase | Purpose |
|------|-------|---------|
| `configs/lanes.yaml` | 1 | Default lane concurrency caps |
| `configs/compaction.yaml` | 3 | Compaction engine settings |
| `configs/tool-profiles.yaml` | 4 | Tool sandbox profile presets |
| `configs/webhooks.yaml` | 5 | Outbound webhook registrations |
| `campaign-packs/_marketplace/manifest-schema.json` | 2 | Pack manifest JSON Schema |

### Files Modified

| File | Phases | Changes |
|------|--------|---------|
| `src/openeinstein/campaigns/executor.py` | 1,3,5,6 | Lane-aware dispatch, compaction integration, harness lifecycle, sandbox wiring |
| `src/openeinstein/campaigns/state.py` | 1 | ConcurrentStepTracker, lane_status property |
| `src/openeinstein/campaigns/config.py` | 6 | harness_type and sandbox_mode fields |
| `src/openeinstein/campaigns/__init__.py` | 1,2 | Exports for lanes, queue modes |
| `src/openeinstein/skills/models.py` | 2 | SkillSource enum, version field, PackManifest |
| `src/openeinstein/skills/registry.py` | 2 | Precedence-aware discovery, list_with_precedence() |
| `src/openeinstein/skills/__init__.py` | 2 | Exports for versioning, installer |
| `src/openeinstein/agents/orchestrator.py` | 3 | CompactionEngine and ContextPinRegistry integration |
| `src/openeinstein/agents/__init__.py` | 3,6 | Exports for compaction, pins, flush, harness |
| `src/openeinstein/security/core.py` | 2,4 | SKILL_MD_INJECTION rules, ToolSandboxProfile, ToolProfileRegistry, enforce_budget() |
| `src/openeinstein/security/__init__.py` | 4,6 | Exports for signing, sandbox |
| `src/openeinstein/gateway/hooks.py` | 4,5 | 6 new hook points, ToolSandboxHook, WebhookBridgeHook, build_default_hook_registry |
| `src/openeinstein/gateway/policy.py` | 4 | Budget fields on PolicyInvariants |
| `src/openeinstein/gateway/__init__.py` | 5,7 | Exports for webhooks, idempotency, hook factory |
| `src/openeinstein/gateway/ws/protocol.py` | 7 | idempotency_key, client_id, client_version fields |
| `src/openeinstein/gateway/ws/handler.py` | 7 | IdempotencyCache integration, client identity tracking |
| `src/openeinstein/routing/router.py` | 4 | CircuitBreaker wired into run_with_fallback |
| `src/openeinstein/persistence/db.py` | 3 | context_pins and durable_notes tables + CRUD |
| `src/openeinstein/persistence/__init__.py` | 3 | Exports for new record types |
| `src/openeinstein/cli/main.py` | 1,2,5 | --parallel-lanes, pack/skill commands, webhook add/remove/list/test |

## Testing Status

**Total tests:** 540 passed, 2 skipped (pre-existing, unrelated)
**Type checking:** mypy clean (89 source files, 0 issues)
**Linting:** ruff clean (all checks passed)

### Test Files (26 total)

**Unit Tests (19 files):**
test_lanes, test_queue_modes, test_skill_versioning, test_skill_precedence, test_pack_installer, test_compaction, test_context_pins, test_memory_flush, test_harness, test_session_sandbox, test_signing, test_tool_profiles, test_circuit_breaker, test_gateway_budget, test_webhooks, test_new_hook_points, test_ws_protocol, test_idempotency, test_cli_lanes

**Integration Tests (7 files):**
test_concurrent_campaign, test_skill_precedence, test_pack_cli_integration, test_compaction_integration, test_tool_sandbox_integration, test_webhook_bridge_integration, test_harness_integration

## Integration Verification

All 18 key classes verified with production call sites:

- LaneRegistry: instantiated in executor.py
- QueueModeHandler: instantiated as default in executor.py
- PackInstaller: instantiated from CLI
- PackSigner: called from installer.py during install
- ToolSandboxProfile/ToolProfileRegistry: instantiated via build_default_hook_registry
- ToolSandboxHook: registered via register_hooks_from_yaml
- WebhookBridgeHook: registered via register_hooks_from_yaml
- WebhookDispatcher: instantiated via build_default_hook_registry
- CompactionEngine: used by orchestrator.py
- ContextPinRegistry: used by orchestrator.py
- MemoryFlushManager: used by executor.py
- RuntimeHarness/PydanticAIHarness/HarnessFactory: used by executor.py
- SessionSandbox: created at run start in executor.py
- ScopedApprovalsStore: created at run start in executor.py
- IdempotencyCache: module-level instance in ws/handler.py
- CircuitBreaker: wired into ModelRouter.run_with_fallback
- build_default_hook_registry: exported from gateway package
