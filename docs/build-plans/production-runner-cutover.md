# OpenEinstein Production Runner Cutover

## Purpose
Execute a single-cutover redesign that moves OpenEinstein from control-plane stubs to a real campaign runtime with a full agent loop, durable replay, policy enforcement, and production qualification gates.

## Scope Lock
- Target: local single-user runtime.
- Rollout: single cutover.
- Compatibility: major redesign allowed.
- Connectors: core required, plugin optional.
- LLM release gate: 3 live providers.

## Requirement Matrix

### Objective Platform Criteria (§23.1)

| Req ID | Requirement | Contract IDs | Verification |
|---|---|---|---|
| PR-OBJ-01 | `pip install openeinstein` clean install works | IC-PR-12 | `tests/production/test_quickstart_install_e2e.py` + `tests/integration/test_packaging_install.py` |
| PR-OBJ-02 | New campaign pack runs without core-code edits | IC-PR-02, IC-PR-11 | `tests/production/test_campaign_pack_extensibility.py` |
| PR-OBJ-03 | Works with at least 3 LLM providers | IC-PR-04 | `tests/production/test_three_live_provider_qualification.py` |
| PR-OBJ-04 | Crash recovery and resume works | IC-PR-06 | `tests/production/test_crash_resume_replay.py` |
| PR-OBJ-05 | `openeinstein eval` runs skill/campaign/persona | IC-PR-09 | `tests/production/test_subjective_intent_evals.py` + existing eval suite |
| PR-OBJ-06 | `openeinstein scan` detects risky patterns | IC-PR-07 | `tests/production/test_policy_enforcement_end_to_end.py` |
| PR-OBJ-07 | First campaign pack runs end-to-end | IC-PR-02, IC-PR-03 | `tests/production/test_full_agent_loop_e2e.py` |

### First Campaign Pack Criteria (§23.2)

| Req ID | Requirement | Contract IDs | Verification |
|---|---|---|---|
| PR-PACK-01 | Viable candidate or documented null result | IC-PR-10 | `tests/production/test_full_agent_loop_e2e.py` |
| PR-PACK-02 | Classified failure map | IC-PR-10 | `tests/production/test_full_agent_loop_e2e.py` |
| PR-PACK-03 | Derivation/artifact traceability per candidate path | IC-PR-08, IC-PR-10 | `tests/production/test_runner_lifecycle_contract.py` |
| PR-PACK-04 | Next-steps synthesis present | IC-PR-10 | `tests/production/test_full_agent_loop_e2e.py` |

### Subjective Intent Criteria (§1.2/§15/§17)

| Req ID | Intent Signal | Contract IDs | Verification |
|---|---|---|---|
| PR-SUBJ-01 | Model-agnostic role routing (no provider hardcoding) | IC-PR-04 | static guard tests + `tests/production/test_three_live_provider_qualification.py` |
| PR-SUBJ-02 | Domain-agnostic core runtime, pack-extensible specialization | IC-PR-02, IC-PR-11 | `tests/production/test_campaign_pack_extensibility.py` |
| PR-SUBJ-03 | Evals-first, trace-first instrumentation | IC-PR-08, IC-PR-09 | `tests/production/test_subjective_intent_evals.py` |
| PR-SUBJ-04 | Contract-led autonomous build loop and audits | IC-PR-01..12 | `docs/audits/production-audit-*.md` |

## Integration Contract Set

- IC-PR-01 Run Lifecycle Contract
- IC-PR-02 Campaign Executor Contract
- IC-PR-03 Agent Loop Contract
- IC-PR-04 Model Routing Contract
- IC-PR-05 ToolBus Runtime Contract
- IC-PR-06 Persistence Contract
- IC-PR-07 Security Contract
- IC-PR-08 Observability Contract
- IC-PR-09 Eval Contract
- IC-PR-10 Report Contract
- IC-PR-11 UI Contract
- IC-PR-12 Packaging/Install Contract

## Work Packages (Red/Green)

### WP-0 Baseline + Contract Matrix
- Deliver this file + ledger entries with executable mappings.
- Exit gate: every criterion above maps to at least one test.

### WP-1 Production Tests First
- Add `tests/production/` suite.
- Red gate: tests fail against pre-cutover runtime.
- Green gate: all pass with production profile controls.

### WP-2 Runtime Redesign
- Add `CampaignExecutor` and runtime services.
- Route CLI and API run start/resume/stop through executor.

### WP-3 Persistence + Recovery
- Add durable runtime tables and replay cursor sequencing.
- Ensure deterministic crash resume at step boundaries.

### WP-4 Agent Loop Wiring
- Enforce deterministic sandwich: precheck -> role-routed reasoning -> postcheck.
- Persist step outputs and retry traces.

### WP-5 Provider Qualification
- Centralize LLM calls through model router roles.
- Record usage/cost.

### WP-6 ToolBus Runtime
- Initialize ToolBus from runtime config.
- Report plugin optionality in health/events.

### WP-7 Security E2E
- Enforce policy + approval checks on risky paths.
- Verify denial/approval behavior with auditable events.

### WP-8 API/CLI/UI Cutover
- Provide `/api/v2/*` runtime contract.
- Update route behavior for real executor state/events.

### WP-9 Reporting + Subjective Evals
- Ensure candidate map, failure map, trace links, next steps.
- Run objective and subjective rubric suites.

### WP-10 Packaging + Release Audit
- Qualify clean install + quickstart on production runtime.
- Execute release readiness audit with residual risks.

## Regression Policy
- No silent test-count reduction.
- No unexpected skips in production profile.
- Phase boundary reruns: unit + integration + production + eval + packaging.

## Production Profile Contract
- Marker: `@pytest.mark.production`.
- Script: `scripts/verify-production-profile.py`.
- Fail conditions:
  - unexpected skips
  - xfail/xpass in production suite
  - missing live-provider qualification when enforcement flag is enabled.

## Audit Deliverables
- `docs/audits/production-audit-a.md`
- `docs/audits/production-audit-b.md`
- `docs/audits/production-audit-c.md`
- `docs/audits/production-audit-release.md`
