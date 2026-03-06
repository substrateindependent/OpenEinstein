"""System-level API routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from openeinstein import __version__
from openeinstein.gateway.auth import DashboardAuthService, auth_state_summary
from openeinstein.gateway.web.config import DashboardConfig


class RemoteCheckRequest(BaseModel):
    origin: str


class WebhookTestRequest(BaseModel):
    url: str


class EmailTestRequest(BaseModel):
    email: str


def build_system_router(
    config: DashboardConfig,
    auth_service: DashboardAuthService,
    *,
    protocol_version: str = "v1",
) -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/version")
    def version() -> dict[str, str]:
        return {"gateway": __version__, "ui": "control-ui", "protocol": protocol_version}

    @router.get("/system")
    def system_summary() -> dict[str, object]:
        return {
            "base_path": config.base_path,
            "bind": config.bind,
            "port": config.port,
            "auth": auth_state_summary(auth_service),
        }

    @router.post("/system/remote/check")
    def remote_check(payload: RemoteCheckRequest) -> dict[str, object]:
        origin = payload.origin.strip().lower()
        local = origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost")
        if local:
            return {"allowed": True, "message": "Local origin is allowed."}
        if config.allow_insecure_remote:
            return {"allowed": True, "message": "Insecure remote mode explicitly enabled."}
        if origin.startswith("https://"):
            return {"allowed": True, "message": "Secure remote origin accepted."}
        return {"allowed": False, "message": "Remote access requires HTTPS or tunnel."}

    @router.post("/system/webhook/test")
    def webhook_test(payload: WebhookTestRequest) -> dict[str, object]:
        return {"ok": True, "message": f"Webhook dispatched: {payload.url}"}

    @router.post("/system/email/test")
    def email_test(payload: EmailTestRequest) -> dict[str, object]:
        return {"ok": True, "message": f"Email dispatched: {payload.email}"}

    return router
