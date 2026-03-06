# Production Audit C

## Scope
Security and policy deep audit after WP-7.

## Findings
- Low: Policy checks are machine-enforced in executor risky path (`network_fetch`) with approval gating.
- Low: Approval-denied and approval-granted paths both covered in production tests.
- Low: Optional plugin absence is surfaced as explicit runtime events (`plugin_optional_missing`) instead of silent pass-through.

## Evidence
- `.venv/bin/pytest tests/production/test_policy_enforcement_end_to_end.py -q`
- `.venv/bin/pytest tests/unit/test_security.py tests/integration/test_security_cli_integration.py -q`

## Unmet Contracts
- Live provider enforcement remains environment-gated and must be enabled for release (`OPENEINSTEIN_ENFORCE_LIVE_PROVIDER_TESTS=1`).

## Remediation
- Added `scripts/verify-production-profile.py` to fail on unexpected skips and enforce live-provider gate when enabled.

## Decision
- Go with release gate condition: enable live-provider enforcement in final qualification environment.
