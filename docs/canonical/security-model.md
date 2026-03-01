# Security Model

## Purpose

Defines machine-enforced safeguards for tool execution, secrets handling, and approval workflows.

## Core Components

- `PolicyEngine`: validates every tool call against `configs/POLICY.json`.
- `ApprovalsStore`: tracks approval requirements and decisions.
- `SecretRedactor`: removes secrets from logs/events/artifacts.
- `SecretsProvider`: retrieves scoped secrets without leaking raw values.
- `Scan Engine`: static and config scanner for risky patterns.

## Invariants

- Prompt text cannot override policy decisions.
- Approval-required actions are blocked until explicitly approved.
- Sensitive values are redacted before persistence/logging.
- Security failures emit audit events and do not silently pass.
