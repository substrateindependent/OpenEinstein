"""Dashboard HTTP API routers."""

from openeinstein.gateway.api.approvals import build_approvals_router
from openeinstein.gateway.api.artifacts import build_artifacts_router
from openeinstein.gateway.api.auth import build_auth_router
from openeinstein.gateway.api.config import build_config_router
from openeinstein.gateway.api.intent import build_intent_router
from openeinstein.gateway.api.runs import build_runs_router
from openeinstein.gateway.api.system import build_system_router
from openeinstein.gateway.api.tools import build_tools_router

__all__ = [
    "build_approvals_router",
    "build_artifacts_router",
    "build_auth_router",
    "build_config_router",
    "build_intent_router",
    "build_runs_router",
    "build_system_router",
    "build_tools_router",
]
