"""Pairing and authentication API routes."""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

from openeinstein.gateway.auth import DashboardAuthService


class PairCompleteRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)
    remember_device: bool = False


def build_auth_router(auth_service: DashboardAuthService) -> APIRouter:
    router = APIRouter(prefix="/pair", tags=["auth"])

    @router.post("/start")
    def start_pairing() -> dict[str, str]:
        session = auth_service.start_pairing()
        return {"code": session.code, "expires_at": session.expires_at}

    @router.post("/complete")
    def complete_pairing(payload: PairCompleteRequest) -> dict[str, str]:
        token = auth_service.complete_pairing(
            payload.code, remember_device=payload.remember_device
        )
        return {"token": token}

    return router
