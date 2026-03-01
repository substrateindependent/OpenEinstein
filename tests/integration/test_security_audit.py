"""Phase 7 security-audit integration coverage."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from openeinstein.agents import AgentOrchestrator
from openeinstein.cli.main import app
from openeinstein.gateway import load_policy
from openeinstein.gateway.policy import PolicyConfig, PolicyInvariants
from openeinstein.security import (
    ApprovalRequiredError,
    ApprovalsStore,
    PolicyEngine,
    PolicyEnforcementHook,
    PolicyViolationError,
    SecureToolGateway,
)
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, PythonSandboxMCPServer, ToolBus


def test_security_audit_scan_approvals_and_sandbox(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    risky = tmp_path / "risky.py"
    risky.write_text(
        "import subprocess\nsubprocess.run('echo bad', shell=True)\nimport os\nos.system('echo bad')\n",
        encoding="utf-8",
    )
    scan_result = runner.invoke(app, ["scan", str(risky)])
    assert scan_result.exit_code == 1
    assert "SHELL_TRUE" in scan_result.stdout
    assert "OS_SYSTEM" in scan_result.stdout

    manager = MCPConnectionManager()
    manager.register_server("local", InMemoryToolServer({"echo": lambda args: args}))
    manager.register_server("sandbox", PythonSandboxMCPServer(tmp_path / "sandbox"))
    bus = ToolBus(manager)

    approvals = ApprovalsStore(tmp_path / ".openeinstein" / "approvals.json")
    policy = PolicyConfig(
        version="1.0",
        invariants=PolicyInvariants(
            require_approval_for=["shell_exec"],
            max_llm_calls_per_step=50,
            max_cas_timeout_minutes=30,
            forbidden_operations=["rm_rf"],
            require_verification_after_gates=True,
        ),
        enforced_by="gateway",
        note="security audit fixture",
    )
    gateway = SecureToolGateway(PolicyEnforcementHook(PolicyEngine(policy, approvals)), bus)

    with pytest.raises(ApprovalRequiredError):
        gateway.call_tool(
            action="shell_exec",
            server="local",
            tool="echo",
            args={"ok": True},
            run_id="audit-1",
        )

    approvals.grant("shell_exec")
    allowed = gateway.call_tool(
        action="shell_exec",
        server="local",
        tool="echo",
        args={"ok": True},
        run_id="audit-2",
    )
    assert allowed.success
    assert allowed.output["ok"] is True

    with pytest.raises(PolicyViolationError):
        gateway.call_tool(
            action="rm_rf",
            server="local",
            tool="echo",
            args={"ok": False},
            run_id="audit-3",
        )

    blocked = bus.call("sandbox", "execute", {"code": "import socket\nresult = 1"})
    assert blocked.success is False
    assert "Forbidden import" in (blocked.error or "")


def test_security_audit_policy_invariants_survive_compaction() -> None:
    policy = load_policy(Path("configs/POLICY.json"))
    invariants = [
        f"require_approval_for={','.join(policy.invariants.require_approval_for)}",
        f"forbidden_operations={','.join(policy.invariants.forbidden_operations)}",
        f"require_verification_after_gates={policy.invariants.require_verification_after_gates}",
    ]

    orchestrator = AgentOrchestrator({}, invariants=invariants, max_compacted_chars=140)
    compacted = orchestrator.compact_with_invariants("x" * 2000, invariants)

    for invariant in invariants:
        assert invariant in compacted
