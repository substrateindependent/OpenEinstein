"""Integration tests for Tool Sandbox Hook (Story 4.5)."""

from __future__ import annotations

from unittest.mock import MagicMock

from openeinstein.gateway.hooks import (
    HookContext,
    HookRegistry,
    HookedToolGateway,
    ToolSandboxHook,
)
from openeinstein.security.core import ToolProfileRegistry, ToolSandboxProfile
from openeinstein.tools import ToolResult


# --- ToolSandboxHook unit tests ---


class TestToolSandboxHook:
    def test_blocks_network_when_denied(self) -> None:
        """Tool with allow_network=False should be blocked for network calls."""
        registry = ToolProfileRegistry()
        registry.register_profile(
            ToolSandboxProfile(
                tool_name_pattern="restricted_tool",
                allow_network=False,
            )
        )
        hook = ToolSandboxHook(registry)
        ctx = HookContext(
            hook_point="before_tool_call",
            tool="restricted_tool",
            action="network_call",
            payload={"requires_network": True},
        )
        response = hook(ctx)
        assert response is not None
        assert response.allow is False
        assert "network" in (response.reason or "").lower()

    def test_allows_permitted_tool(self) -> None:
        """Tool with required permissions should pass."""
        registry = ToolProfileRegistry()
        registry.register_profile(
            ToolSandboxProfile(
                tool_name_pattern="arxiv_search",
                allow_network=True,
            )
        )
        hook = ToolSandboxHook(registry)
        ctx = HookContext(
            hook_point="before_tool_call",
            tool="arxiv_search",
            action="search",
            payload={"requires_network": True},
        )
        response = hook(ctx)
        assert response is None or response.allow is True

    def test_blocks_shell_when_denied(self) -> None:
        registry = ToolProfileRegistry()
        # minimal preset: no shell allowed
        hook = ToolSandboxHook(registry)
        ctx = HookContext(
            hook_point="before_tool_call",
            tool="some_tool",
            action="execute",
            payload={"requires_shell": True},
        )
        response = hook(ctx)
        assert response is not None
        assert response.allow is False

    def test_blocks_fs_write_when_denied(self) -> None:
        registry = ToolProfileRegistry()
        hook = ToolSandboxHook(registry)
        ctx = HookContext(
            hook_point="before_tool_call",
            tool="some_tool",
            action="write",
            payload={"requires_fs_write": True},
        )
        response = hook(ctx)
        assert response is not None
        assert response.allow is False

    def test_allows_when_no_special_requirements(self) -> None:
        """Tool call with no special requirements should pass even with minimal profile."""
        registry = ToolProfileRegistry()
        hook = ToolSandboxHook(registry)
        ctx = HookContext(
            hook_point="before_tool_call",
            tool="simple_tool",
            action="read",
            payload={},
        )
        response = hook(ctx)
        assert response is None or response.allow is True

    def test_fail_closed_on_error(self) -> None:
        """If profile lookup fails, default to deny (fail-closed)."""
        registry = MagicMock(spec=ToolProfileRegistry)
        registry.get_profile.side_effect = Exception("registry error")
        hook = ToolSandboxHook(registry)
        ctx = HookContext(
            hook_point="before_tool_call",
            tool="any_tool",
            action="action",
            payload={"requires_network": True},
        )
        response = hook(ctx)
        assert response is not None
        assert response.allow is False

    def test_none_tool_passes(self) -> None:
        """Hook with no tool name should pass (not applicable)."""
        registry = ToolProfileRegistry()
        hook = ToolSandboxHook(registry)
        ctx = HookContext(
            hook_point="before_tool_call",
            action="action",
        )
        response = hook(ctx)
        assert response is None or response.allow is True


# --- Integration with HookedToolGateway ---


class TestToolSandboxGatewayIntegration:
    def test_blocked_tool_via_gateway(self) -> None:
        """Tool blocked by sandbox profile returns failure through gateway."""
        registry = ToolProfileRegistry()
        hook = ToolSandboxHook(registry)

        hook_registry = HookRegistry()
        hook_registry.register("before_tool_call", hook)

        mock_bus = MagicMock()
        mock_bus.call.return_value = ToolResult(success=True)

        gateway = HookedToolGateway(tool_bus=mock_bus, hooks=hook_registry)
        result = gateway.call_tool(
            action="shell_exec",
            server="local",
            tool="unknown_tool",
            args={"requires_shell": True},
        )
        assert not result.success
        mock_bus.call.assert_not_called()

    def test_permitted_tool_via_gateway(self) -> None:
        """Permitted tool call passes through sandbox and executes."""
        registry = ToolProfileRegistry()
        registry.register_profile(
            ToolSandboxProfile(
                tool_name_pattern="safe_tool",
                allow_network=True,
                allow_fs_write=True,
                allow_shell=True,
            )
        )
        hook = ToolSandboxHook(registry)

        hook_registry = HookRegistry()
        hook_registry.register("before_tool_call", hook)

        mock_bus = MagicMock()
        mock_bus.call.return_value = ToolResult(success=True, data={"ok": True})

        gateway = HookedToolGateway(tool_bus=mock_bus, hooks=hook_registry)
        result = gateway.call_tool(
            action="read",
            server="local",
            tool="safe_tool",
            args={},
        )
        assert result.success
        mock_bus.call.assert_called_once()

    def test_no_registry_defaults_to_minimal(self) -> None:
        """When ToolProfileRegistry is default, unknown tools get minimal."""
        registry = ToolProfileRegistry()  # no custom profiles
        hook = ToolSandboxHook(registry)

        hook_registry = HookRegistry()
        hook_registry.register("before_tool_call", hook)

        mock_bus = MagicMock()
        mock_bus.call.return_value = ToolResult(success=True)

        gateway = HookedToolGateway(tool_bus=mock_bus, hooks=hook_registry)

        # Network call should be blocked by minimal
        result = gateway.call_tool(
            action="fetch",
            server="remote",
            tool="unknown_tool",
            args={"requires_network": True},
        )
        assert not result.success
