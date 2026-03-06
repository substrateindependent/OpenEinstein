"""Gateway primitives and policy loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openeinstein.gateway.control_plane import (
    ArtifactRecord,
    ControlPlane,
    FileBackedControlPlane,
    RunEvent,
    RunRecord,
    RunStatus,
)
from openeinstein.gateway.hooks import (
    ApprovalGateHook,
    AuditLoggerHook,
    Hook,
    HookContext,
    HookDispatchResult,
    HookFactory,
    HookPoint,
    HookRegistry,
    HookResponse,
    HookedToolGateway,
    build_default_hook_registry,
    register_hooks_from_yaml,
)
from openeinstein.gateway.policy import PolicyConfig, PolicyLoadError, load_policy
from openeinstein.gateway.web import DashboardConfig, DashboardDeps, create_dashboard_app
from openeinstein.gateway.idempotency import IdempotencyCache
from openeinstein.gateway.webhooks import WebhookDispatcher

if TYPE_CHECKING:
    from openeinstein.gateway.runtime_control import ExecutorBackedControlPlane

__all__ = [
    "ApprovalGateHook",
    "ArtifactRecord",
    "AuditLoggerHook",
    "build_default_hook_registry",
    "ControlPlane",
    "create_dashboard_app",
    "DashboardConfig",
    "DashboardDeps",
    "ExecutorBackedControlPlane",
    "FileBackedControlPlane",
    "Hook",
    "HookContext",
    "HookDispatchResult",
    "HookFactory",
    "HookPoint",
    "HookRegistry",
    "HookResponse",
    "HookedToolGateway",
    "IdempotencyCache",
    "PolicyConfig",
    "PolicyLoadError",
    "RunEvent",
    "RunRecord",
    "RunStatus",
    "load_policy",
    "register_hooks_from_yaml",
    "WebhookDispatcher",
]


def __getattr__(name: str) -> object:
    if name == "ExecutorBackedControlPlane":
        from openeinstein.gateway.runtime_control import ExecutorBackedControlPlane

        return ExecutorBackedControlPlane
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
