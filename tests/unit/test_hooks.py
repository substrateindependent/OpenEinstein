"""Unit tests for gateway hook dispatch."""

from __future__ import annotations

import json
from pathlib import Path

from openeinstein.gateway import (
    ApprovalGateHook,
    AuditLoggerHook,
    HookContext,
    HookRegistry,
)
from openeinstein.gateway.policy import PolicyConfig
from openeinstein.security import ApprovalsStore, PolicyEngine


def _policy() -> PolicyConfig:
    return PolicyConfig.model_validate(
        {
            "version": "1.0",
            "invariants": {
                "require_approval_for": ["shell_exec"],
                "max_llm_calls_per_step": 50,
                "max_cas_timeout_minutes": 60,
                "forbidden_operations": [],
                "require_verification_after_gates": True,
            },
            "enforced_by": "gateway",
            "note": "test",
        }
    )


def test_before_tool_call_hook_blocks_without_approval(tmp_path: Path) -> None:
    approvals = ApprovalsStore(tmp_path / "approvals.json")
    engine = PolicyEngine(_policy(), approvals)

    hooks = HookRegistry()
    hooks.register("before_tool_call", ApprovalGateHook(engine))

    blocked = hooks.dispatch(
        "before_tool_call",
        HookContext(hook_point="before_tool_call", action="shell_exec"),
    )
    assert blocked.allow is False

    approvals.grant("shell_exec")
    allowed = hooks.dispatch(
        "before_tool_call",
        HookContext(hook_point="before_tool_call", action="shell_exec"),
    )
    assert allowed.allow is True


def test_after_tool_call_hook_logs_call_details(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    hooks = HookRegistry()
    hooks.register("after_tool_call", AuditLoggerHook(audit_path))

    dispatched = hooks.dispatch(
        "after_tool_call",
        HookContext(
            hook_point="after_tool_call",
            run_id="run-1",
            action="shell_exec",
            server="local",
            tool="echo",
            payload={"success": True},
        ),
    )
    assert dispatched.allow is True
    line = audit_path.read_text(encoding="utf-8").splitlines()[0]
    payload = json.loads(line)
    assert payload["hook_point"] == "after_tool_call"
    assert payload["tool"] == "echo"


def test_campaign_state_transition_hook_fires_with_nonfatal_errors() -> None:
    fired: list[str] = []

    def good_hook(context: HookContext) -> None:
        fired.append(context.payload["to"])

    def bad_hook(context: HookContext) -> None:  # noqa: ARG001
        raise RuntimeError("boom")

    hooks = HookRegistry()
    hooks.register("campaign_state_transition", good_hook)
    hooks.register("campaign_state_transition", bad_hook)

    result = hooks.dispatch(
        "campaign_state_transition",
        HookContext(
            hook_point="campaign_state_transition",
            run_id="run-2",
            payload={"from": "running", "to": "stopped"},
        ),
    )
    assert result.allow is True
    assert fired == ["stopped"]
    assert len(result.errors) == 1
