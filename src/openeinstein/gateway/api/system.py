"""System-level API routes."""

from __future__ import annotations

from fastapi import APIRouter

from openeinstein import __version__
from openeinstein.gateway.auth import DashboardAuthService, auth_state_summary
from openeinstein.gateway.web.config import DashboardConfig


def build_system_router(config: DashboardConfig, auth_service: DashboardAuthService) -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/version")
    def version() -> dict[str, str]:
        return {"gateway": __version__, "ui": "control-ui", "protocol": "v1"}

    @router.get("/system")
    def system_summary() -> dict[str, object]:
        return {
            "base_path": config.base_path,
            "bind": config.bind,
            "port": config.port,
            "auth": auth_state_summary(auth_service),
        }

    return router
