"""Hook registry and dispatch system for gateway extension points."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Literal, Protocol

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from openeinstein.security import PolicyEngine
from openeinstein.security.core import ToolProfileRegistry
from openeinstein.tools import ToolBus, ToolResult

_logger = logging.getLogger(__name__)

HookPoint = Literal[
    "before_tool_call",
    "after_tool_call",
    "campaign_state_transition",
    "before_run_start",
    "after_run_end",
    "before_compaction",
    "after_compaction",
    "candidate_generated",
    "gate_passed",
    "gate_failed",
    "budget_warning",
]


class HookContext(BaseModel):
    """Context payload delivered to hooks."""

    hook_point: HookPoint
    run_id: str | None = None
    action: str | None = None
    server: str | None = None
    tool: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class HookResponse(BaseModel):
    """Result of a hook callback."""

    allow: bool = True
    reason: str | None = None


class HookDispatchResult(BaseModel):
    """Aggregate dispatch output."""

    allow: bool = True
    reasons: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class Hook(Protocol):
    def __call__(self, context: HookContext) -> HookResponse | None: ...


class HookRegistry:
    """Registers and dispatches hooks by point."""

    def __init__(self) -> None:
        self._hooks: dict[HookPoint, list[Hook]] = {
            "before_tool_call": [],
            "after_tool_call": [],
            "campaign_state_transition": [],
            "before_run_start": [],
            "after_run_end": [],
            "before_compaction": [],
            "after_compaction": [],
            "candidate_generated": [],
            "gate_passed": [],
            "gate_failed": [],
            "budget_warning": [],
        }

    def register(self, hook_point: HookPoint, hook: Hook) -> None:
        self._hooks[hook_point].append(hook)

    def dispatch(self, hook_point: HookPoint, context: HookContext) -> HookDispatchResult:
        result = HookDispatchResult(allow=True)
        for hook in self._hooks[hook_point]:
            try:
                response = hook(context)
            except Exception as exc:
                result.errors.append(f"{hook_point}: {exc}")
                continue
            if response is None:
                continue
            if not response.allow:
                result.allow = False
                if response.reason:
                    result.reasons.append(response.reason)
        return result


class AuditLoggerHook:
    """Writes hook invocations to JSONL audit logs."""

    def __init__(self, path: str | Path = Path(".openeinstein") / "hooks-audit.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, context: HookContext) -> HookResponse:
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "hook_point": context.hook_point,
            "run_id": context.run_id,
            "action": context.action,
            "server": context.server,
            "tool": context.tool,
            "payload": context.payload,
        }
        with self._path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry))
            stream.write("\n")
        return HookResponse(allow=True)


class ApprovalGateHook:
    """Blocks calls that violate policy approvals."""

    def __init__(self, policy_engine: PolicyEngine) -> None:
        self._policy_engine = policy_engine

    def __call__(self, context: HookContext) -> HookResponse:
        if context.action is None:
            return HookResponse(allow=True)
        try:
            self._policy_engine.enforce_action(context.action)
        except PermissionError as exc:
            return HookResponse(allow=False, reason=str(exc))
        return HookResponse(allow=True)


def register_hooks_from_yaml(
    *,
    registry: HookRegistry,
    config_path: str | Path,
    policy_engine: PolicyEngine | None = None,
    audit_path: str | Path = Path(".openeinstein") / "hooks-audit.jsonl",
    tool_profile_registry: ToolProfileRegistry | None = None,
    webhook_dispatcher: Any | None = None,  # noqa: ANN401
) -> None:
    """Register built-in hooks from YAML config."""
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    configured = payload.get("hooks", {})
    if not isinstance(configured, dict):
        return

    for point_raw, hook_specs in configured.items():
        point = point_raw
        if point not in registry._hooks:  # noqa: SLF001 - internal validation helper
            continue
        if not isinstance(hook_specs, list):
            continue
        for hook_spec in hook_specs:
            if not isinstance(hook_spec, dict):
                continue
            hook_type = hook_spec.get("type")
            if hook_type == "audit":
                registry.register(
                    point,  # type: ignore[arg-type]
                    AuditLoggerHook(hook_spec.get("path", audit_path)),
                )
            if hook_type == "approval_gate" and policy_engine is not None:
                registry.register(point, ApprovalGateHook(policy_engine))  # type: ignore[arg-type]
            if hook_type == "tool_sandbox" and tool_profile_registry is not None:
                registry.register(point, ToolSandboxHook(tool_profile_registry))  # type: ignore[arg-type]
            if hook_type == "webhook_bridge" and webhook_dispatcher is not None:
                registry.register(point, WebhookBridgeHook(webhook_dispatcher))  # type: ignore[arg-type]


class HookedToolGateway:
    """Runtime path that enforces before/after hooks around ToolBus calls."""

    def __init__(self, tool_bus: ToolBus, hooks: HookRegistry) -> None:
        self._tool_bus = tool_bus
        self._hooks = hooks

    def call_tool(
        self,
        *,
        action: str,
        server: str,
        tool: str,
        args: dict[str, Any],
        run_id: str | None = None,
    ) -> ToolResult:
        before_context = HookContext(
            hook_point="before_tool_call",
            run_id=run_id,
            action=action,
            server=server,
            tool=tool,
            payload=args,
        )
        before = self._hooks.dispatch("before_tool_call", before_context)
        if not before.allow:
            reason = before.reasons[0] if before.reasons else "blocked by hook"
            return ToolResult(success=False, error=reason)

        result = self._tool_bus.call(server, tool, args, run_id=run_id)

        after_context = HookContext(
            hook_point="after_tool_call",
            run_id=run_id,
            action=action,
            server=server,
            tool=tool,
            payload={"success": result.success, "error": result.error},
        )
        self._hooks.dispatch("after_tool_call", after_context)
        return result


class ToolSandboxHook:
    """Enforces per-tool sandbox profiles at the ``before_tool_call`` hook point.

    Checks the tool call payload for ``requires_network``, ``requires_shell``,
    and ``requires_fs_write`` flags against the resolved ``ToolSandboxProfile``.
    Defaults to deny (fail-closed) on any lookup error.
    """

    def __init__(self, profile_registry: ToolProfileRegistry) -> None:
        self._registry = profile_registry

    def __call__(self, context: HookContext) -> HookResponse | None:
        if context.tool is None:
            return None

        try:
            profile = self._registry.get_profile(context.tool)
        except Exception:
            _logger.exception("ToolSandboxHook: profile lookup failed for %s", context.tool)
            return HookResponse(allow=False, reason="Sandbox profile lookup failed; denying by default")

        payload = context.payload or {}

        if payload.get("requires_network") and not profile.allow_network:
            return HookResponse(
                allow=False,
                reason=f"Tool '{context.tool}' denied network access by sandbox profile",
            )
        if payload.get("requires_shell") and not profile.allow_shell:
            return HookResponse(
                allow=False,
                reason=f"Tool '{context.tool}' denied shell access by sandbox profile",
            )
        if payload.get("requires_fs_write") and not profile.allow_fs_write:
            return HookResponse(
                allow=False,
                reason=f"Tool '{context.tool}' denied filesystem write by sandbox profile",
            )

        return None


class WebhookBridgeHook:
    """Bridges the hook system to the outbound :class:`WebhookDispatcher`.

    When registered on a hook point, it forwards the event to the webhook
    dispatcher which filters by subscription and delivers via HTTP.  Errors
    are caught so the bridge never blocks the hook chain.
    """

    def __init__(self, dispatcher: Any) -> None:  # noqa: ANN401
        from openeinstein.gateway.webhooks import WebhookDispatcher

        if not isinstance(dispatcher, WebhookDispatcher):
            # Accept duck-typed dispatchers (e.g. MagicMock with .dispatch)
            pass
        self._dispatcher = dispatcher

    def __call__(self, context: HookContext) -> HookResponse | None:
        try:
            self._dispatcher.dispatch(
                context.hook_point,
                context.payload,
                blocking=True,
            )
        except Exception:
            _logger.exception(
                "WebhookBridgeHook: dispatch error for %s", context.hook_point
            )
        return None


HookFactory = Callable[[HookContext], HookResponse | None]


def build_default_hook_registry(
    *,
    policy_engine: PolicyEngine | None = None,
    tool_profiles_path: str | Path | None = None,
    webhooks_path: str | Path | None = None,
    hooks_yaml_path: str | Path | None = None,
) -> HookRegistry:
    """Create a hook registry with standard hooks wired from config files.

    This is a convenience factory for production gateway startup.  It
    instantiates ``ToolProfileRegistry``, ``WebhookDispatcher``, and
    registers them via ``register_hooks_from_yaml`` if a hooks config
    is provided.
    """
    registry = HookRegistry()

    # ToolProfileRegistry from YAML (optional)
    profile_registry: ToolProfileRegistry | None = None
    if tool_profiles_path is not None:
        p = Path(tool_profiles_path)
        if p.exists():
            profile_registry = ToolProfileRegistry.from_yaml(p)

    # WebhookDispatcher from YAML (optional)
    webhook_dispatcher = None
    if webhooks_path is not None:
        p = Path(webhooks_path)
        if p.exists():
            from openeinstein.gateway.webhooks import WebhookDispatcher, load_webhook_config

            wh_config = load_webhook_config(p)
            webhook_dispatcher = WebhookDispatcher.from_config(wh_config)

    # Register hooks from YAML config
    if hooks_yaml_path is not None:
        p = Path(hooks_yaml_path)
        if p.exists():
            register_hooks_from_yaml(
                registry=registry,
                config_path=p,
                policy_engine=policy_engine,
                tool_profile_registry=profile_registry,
                webhook_dispatcher=webhook_dispatcher,
            )

    return registry
