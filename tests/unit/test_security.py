"""Unit tests for security subsystem behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.gateway import PolicyConfig
from openeinstein.security import (
    ApprovalRequiredError,
    ApprovalsStore,
    EnvFileSecretsProvider,
    MetadataPinStore,
    PolicyEngine,
    PolicyEnforcementHook,
    PolicyViolationError,
    SecretRedactor,
    SecureToolGateway,
    SecurityScanner,
)
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


def _policy() -> PolicyConfig:
    return PolicyConfig.model_validate(
        {
            "version": "1.0",
            "invariants": {
                "require_approval_for": ["shell_exec"],
                "max_llm_calls_per_step": 50,
                "max_cas_timeout_minutes": 60,
                "forbidden_operations": ["delete_campaign_state"],
                "require_verification_after_gates": True,
            },
            "enforced_by": "gateway",
            "note": "test",
        }
    )


def test_policy_engine_blocks_then_allows_approved_tool_call(tmp_path: Path) -> None:
    approvals = ApprovalsStore(tmp_path / "approvals.json")
    engine = PolicyEngine(_policy(), approvals)
    hook = PolicyEnforcementHook(engine)

    manager = MCPConnectionManager()
    manager.register_server("local", InMemoryToolServer({"echo": lambda args: {"ok": args}}))
    bus = ToolBus(manager)
    gateway = SecureToolGateway(hook, bus)

    with pytest.raises(ApprovalRequiredError):
        gateway.call_tool(action="shell_exec", server="local", tool="echo", args={"x": 1})

    approvals.grant("shell_exec")
    result = gateway.call_tool(action="shell_exec", server="local", tool="echo", args={"x": 1})
    assert result.success
    assert result.output == {"ok": {"x": 1}}

    with pytest.raises(PolicyViolationError):
        engine.enforce_action("delete_campaign_state")


def test_secret_redaction_and_scan_detection(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("API_SECRET=test-secret-value\n", encoding="utf-8")
    provider = EnvFileSecretsProvider(env_path)
    redactor = SecretRedactor.from_provider(provider, ["API_SECRET"])

    assert redactor.redact_text("token=test-secret-value") == "token=[REDACTED]"
    redacted_map = redactor.redact_mapping({"a": "test-secret-value", "b": {"c": "x"}})
    assert redacted_map["a"] == "[REDACTED]"

    risky_file = tmp_path / "risky.py"
    risky_file.write_text("import os\nos.system('echo hi')\n", encoding="utf-8")
    findings = SecurityScanner().scan_paths([risky_file])
    assert any(finding.rule_id == "OS_SYSTEM" for finding in findings)


def test_metadata_hash_pinning(tmp_path: Path) -> None:
    pins = MetadataPinStore(tmp_path / "pins.json")
    digest = pins.pin("manifest", "abc")
    assert isinstance(digest, str)
    assert pins.verify("manifest", "abc") is True
    assert pins.verify("manifest", "xyz") is False
