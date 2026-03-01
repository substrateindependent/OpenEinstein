# OpenEinstein Trust Model

## Operator Boundary

OpenEinstein is an operator-controlled local platform. The operator is the final authority on configuration, approvals, and execution scope.

The platform can:
- Run configured campaign workflows
- Call configured tools through policy-checked gateways
- Persist run state, traces, and artifacts locally
- Generate research artifacts for human review

The platform cannot:
- Override machine policy invariants in `configs/POLICY.json`
- Perform elevated or risky operations without explicit approval
- Treat generated outputs as ground truth without verification
- Substitute for peer review or human scientific judgment

## Security Posture

- Default-deny for risky actions
- Approval checks before protected tool calls
- Sandbox-oriented tool execution policies
- Secret storage via environment or keyring, never hardcoded
- Per-campaign isolation of state and artifacts (implementation target)

## Verification and Accountability

- All major actions should be traceable by run ID
- Policy checks are deterministic and external to prompt context
- Campaign outputs are review artifacts, not autonomous decisions

## Data and Privacy

- Local-first operation by default
- No telemetry required for base operation
- External network actions should be explicit and policy-gated
