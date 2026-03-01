"""Integration tests for hook-driven tool call enforcement."""

from __future__ import annotations

from pathlib import Path

from openeinstein.gateway import (
    ApprovalGateHook,
    AuditLoggerHook,
    HookRegistry,
    HookedToolGateway,
)
from openeinstein.gateway.policy import PolicyConfig
from openeinstein.security import ApprovalsStore, PolicyEngine
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


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


def test_hooked_tool_gateway_blocks_then_allows(tmp_path: Path) -> None:
    approvals = ApprovalsStore(tmp_path / "approvals.json")
    engine = PolicyEngine(_policy(), approvals)
    hooks = HookRegistry()
    hooks.register("before_tool_call", ApprovalGateHook(engine))
    hooks.register("after_tool_call", AuditLoggerHook(tmp_path / "audit.jsonl"))

    manager = MCPConnectionManager()
    manager.register_server("math", InMemoryToolServer({"sum": lambda args: args["a"] + args["b"]}))
    bus = ToolBus(manager)
    gateway = HookedToolGateway(bus, hooks)

    blocked = gateway.call_tool(
        action="shell_exec",
        server="math",
        tool="sum",
        args={"a": 1, "b": 2},
        run_id="run-hook",
    )
    assert blocked.success is False

    approvals.grant("shell_exec")
    allowed = gateway.call_tool(
        action="shell_exec",
        server="math",
        tool="sum",
        args={"a": 1, "b": 2},
        run_id="run-hook",
    )
    assert allowed.success is True
    assert allowed.output == 3
    assert (tmp_path / "audit.jsonl").exists()
