"""Configuration and campaign-pack API routes."""

from __future__ import annotations

import shutil
import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openeinstein.campaigns import CampaignConfigLoader
from openeinstein.security import SecurityScanner
from openeinstein.gateway.web.config import DashboardConfig


class ConfigValidateRequest(BaseModel):
    config: dict[str, Any]


class PackFieldSchema(BaseModel):
    name: str
    label: str
    type: str
    required: bool = False
    default: Any | None = None


class PackInstallRequest(BaseModel):
    pack_id: str = Field(min_length=1)


def _packs_root() -> Path:
    return Path(os.getenv("OPENEINSTEIN_PACKS_ROOT", "campaign-packs"))


def _marketplace_root() -> Path:
    configured = os.getenv("OPENEINSTEIN_MARKETPLACE_ROOT")
    if configured:
        return Path(configured)
    return _packs_root() / "_marketplace"


def _list_pack_dirs(root: Path) -> dict[str, Path]:
    if not root.exists():
        return {}
    discovered: dict[str, Path] = {}
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        if (path / "campaign.yaml").exists():
            discovered[path.name] = path
    return discovered


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
        packs_root = _packs_root()
        loader = CampaignConfigLoader(packs_root)
        packs = loader.discover_packs()
        return {
            "packs": [
                {"id": pack_id, "path": str(path)}
                for pack_id, path in sorted(packs.items(), key=lambda item: item[0])
            ]
        }

    @router.get("/packs/{pack_id}/schema")
    def pack_schema(pack_id: str) -> dict[str, Any]:
        packs_root = _packs_root()
        loader = CampaignConfigLoader(packs_root)
        try:
            loaded = loader.load_pack(pack_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        fields = [
            PackFieldSchema(
                name="search_space.generator_skill",
                label="Generator Skill",
                type="string",
                required=True,
                default=loaded.config.search_space.generator_skill,
            ).model_dump(mode="json")
        ]
        for gate in loaded.config.gate_pipeline:
            fields.append(
                PackFieldSchema(
                    name=f"gate.{gate.name}.timeout_seconds",
                    label=f"{gate.name} timeout (seconds)",
                    type="number",
                    required=False,
                    default=gate.timeout_seconds,
                ).model_dump(mode="json")
            )
        return {
            "pack_id": pack_id,
            "campaign_path": str(loaded.config_path),
            "title": loaded.config.name,
            "description": loaded.config.description,
            "fields": fields,
        }

    @router.get("/packs/marketplace")
    def marketplace_packs() -> dict[str, list[dict[str, Any]]]:
        installed = set(CampaignConfigLoader(_packs_root()).discover_packs())
        packs: list[dict[str, Any]] = []
        for pack_id, path in _list_pack_dirs(_marketplace_root()).items():
            config_payload = yaml.safe_load((path / "campaign.yaml").read_text(encoding="utf-8"))
            campaign = (config_payload or {}).get("campaign", {})
            packs.append(
                {
                    "id": pack_id,
                    "name": campaign.get("name", pack_id),
                    "description": campaign.get("description", ""),
                    "trust_tier": "curated",
                    "installed": pack_id in installed,
                }
            )
        return {"packs": packs}

    @router.post("/packs/install")
    def install_pack(payload: PackInstallRequest) -> dict[str, Any]:
        pack_id = payload.pack_id.strip()
        if not pack_id:
            raise HTTPException(status_code=400, detail="pack_id is required")
        source = _marketplace_root() / pack_id
        if not (source / "campaign.yaml").exists():
            raise HTTPException(status_code=404, detail=f"Unknown marketplace pack: {pack_id}")
        destination = _packs_root() / pack_id
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, dirs_exist_ok=True)
        findings = SecurityScanner().scan_paths([destination])
        return {
            "pack_id": pack_id,
            "installed_path": str(destination),
            "scan_findings": [finding.model_dump(mode="json") for finding in findings],
        }

    @router.get("/config/example")
    def config_example() -> dict[str, Any]:
        path = Path("configs/openeinstein.example.yaml")
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    return router
