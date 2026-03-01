"""Campaign config loader and validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, ValidationError


class CampaignDependencies(BaseModel):
    tools: list[str] = Field(default_factory=list)


class SearchSpaceConfig(BaseModel):
    generator_skill: str = Field(min_length=1)


class GateConfig(BaseModel):
    name: str = Field(min_length=1)
    skill: str = Field(min_length=1)
    cas_requirements: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=30.0, gt=0)


class CampaignDefinition(BaseModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = ""
    search_space: SearchSpaceConfig
    gate_pipeline: list[GateConfig] = Field(default_factory=list)
    dependencies: CampaignDependencies = Field(default_factory=CampaignDependencies)


class CampaignConfigEnvelope(BaseModel):
    campaign: CampaignDefinition


class LoadedCampaignPack(BaseModel):
    pack_name: str
    pack_dir: Path
    config_path: Path
    config: CampaignDefinition


class CampaignConfigLoader:
    """Discover and load campaign packs with capability/dependency validation."""

    def __init__(self, packs_root: str | Path = "campaign-packs") -> None:
        self._packs_root = Path(packs_root)

    def discover_packs(self) -> dict[str, Path]:
        discovered: dict[str, Path] = {}
        if not self._packs_root.exists():
            return discovered
        for path in sorted(self._packs_root.iterdir()):
            if not path.is_dir():
                continue
            config_path = path / "campaign.yaml"
            if config_path.exists():
                discovered[path.name] = path
        return discovered

    def load_pack(self, pack_name: str) -> LoadedCampaignPack:
        packs = self.discover_packs()
        if pack_name not in packs:
            available = ", ".join(sorted(packs)) or "none"
            raise FileNotFoundError(f"Unknown campaign pack '{pack_name}'. Available: {available}")
        pack_dir = packs[pack_name]
        config_path = pack_dir / "campaign.yaml"
        config = self.load_config(config_path)
        return LoadedCampaignPack(
            pack_name=pack_name,
            pack_dir=pack_dir,
            config_path=config_path,
            config=config,
        )

    @staticmethod
    def load_config(path: str | Path) -> CampaignDefinition:
        raw_path = Path(path)
        payload = yaml.safe_load(raw_path.read_text(encoding="utf-8"))
        try:
            envelope = CampaignConfigEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Invalid campaign config at {raw_path}: {exc}") from exc
        return envelope.campaign

    @staticmethod
    def resolve_capabilities(
        gates: list[GateConfig],
        backend_capabilities: dict[str, set[str]],
    ) -> dict[str, list[str]]:
        mapping: dict[str, list[str]] = {}
        for gate in gates:
            requirements = set(gate.cas_requirements)
            compatible = sorted(
                backend_name
                for backend_name, capabilities in backend_capabilities.items()
                if requirements.issubset(capabilities)
            )
            if not compatible:
                raise ValueError(
                    f"No backend satisfies gate '{gate.name}' requirements: "
                    f"{sorted(requirements)}"
                )
            mapping[gate.name] = compatible
        return mapping

    @staticmethod
    def validate_tool_dependencies(
        config: CampaignDefinition,
        available_tools: set[str],
    ) -> None:
        missing = sorted(tool for tool in config.dependencies.tools if tool not in available_tools)
        if missing:
            raise ValueError(f"Missing required tool dependencies: {', '.join(missing)}")

    def validate_runtime_requirements(
        self,
        config: CampaignDefinition,
        *,
        backend_capabilities: dict[str, set[str]],
        available_tools: set[str],
    ) -> dict[str, Any]:
        capability_map = self.resolve_capabilities(config.gate_pipeline, backend_capabilities)
        self.validate_tool_dependencies(config, available_tools)
        return {"capability_map": capability_map, "required_tools": config.dependencies.tools}
