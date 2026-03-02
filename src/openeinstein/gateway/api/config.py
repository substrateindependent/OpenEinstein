"""Configuration and campaign-pack API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from fastapi import APIRouter
from pydantic import BaseModel

from openeinstein.campaigns import CampaignConfigLoader
from openeinstein.gateway.web.config import DashboardConfig


class ConfigValidateRequest(BaseModel):
    config: dict[str, Any]


def build_config_router(config: DashboardConfig) -> APIRouter:
    router = APIRouter(tags=["config"])

    @router.get("/config")
    def get_config() -> dict[str, Any]:
        return config.model_dump(mode="json")

    @router.post("/config/validate")
    def validate_config(payload: ConfigValidateRequest) -> dict[str, Any]:
        proposed = payload.config
        if "model_routing" not in proposed:
            return {"valid": False, "errors": ["Missing required key: model_routing"]}
        return {"valid": True, "errors": []}

    @router.get("/packs")
    def list_packs() -> dict[str, list[dict[str, str]]]:
        packs_root = Path("campaign-packs")
        loader = CampaignConfigLoader(packs_root)
        packs = loader.discover_packs()
        return {
            "packs": [
                {"id": pack_id, "path": str(path)}
                for pack_id, path in sorted(packs.items(), key=lambda item: item[0])
            ]
        }

    @router.get("/config/example")
    def config_example() -> dict[str, Any]:
        path = Path("configs/openeinstein.example.yaml")
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    return router
