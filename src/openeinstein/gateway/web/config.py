"""Dashboard web server configuration and dependency container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from openeinstein.gateway.control_plane import ControlPlane, FileBackedControlPlane
from openeinstein.persistence import CampaignDB
from openeinstein.routing import ModelRouter, load_routing_config
from openeinstein.routing.models import ModelConfig, RoleConfig, RoutingConfig, RoutingRoles, RoutingRoot
from openeinstein.security import ApprovalsStore, PolicyEngine
from openeinstein.tools import ToolBus


def _packaged_static_dir() -> Path:
    return Path(__file__).resolve().parent / "static" / "control-ui"


def _default_static_dir() -> Path:
    packaged = _packaged_static_dir()
    if packaged.exists():
        return packaged
    return Path("dist/control-ui")


def _fallback_router() -> ModelRouter:
    return ModelRouter(
        RoutingConfig(
            model_routing=RoutingRoot(
                roles=RoutingRoles(
                    reasoning=RoleConfig(
                        description="Fallback reasoning role",
                        default=ModelConfig(provider="fallback", model="reasoning"),
                    ),
                    generation=RoleConfig(
                        description="Fallback generation role",
                        default=ModelConfig(provider="fallback", model="generation"),
                    ),
                    fast=RoleConfig(
                        description="Fallback fast role",
                        default=ModelConfig(provider="fallback", model="fast"),
                    ),
                    embeddings=RoleConfig(
                        description="Fallback embeddings role",
                        default=ModelConfig(provider="fallback", model="embeddings"),
                    ),
                )
            )
        )
    )


class DashboardConfig(BaseModel):
    """Control UI server configuration."""

    enabled: bool = True
    base_path: str = "/"
    bind: str = "127.0.0.1"
    port: int = 8420
    allowed_origins: list[str] = Field(default_factory=list)
    allow_insecure_remote: bool = False
    session_timeout_minutes: int = 480
    notifications_enabled: bool = True
    static_dir: Path = Field(default_factory=_default_static_dir)


@dataclass(slots=True)
class DashboardDeps:
    """Dependency container for dashboard route handlers."""

    control_plane: ControlPlane | None = None
    db: CampaignDB | None = None
    approvals_store: ApprovalsStore | None = None
    policy_engine: PolicyEngine | None = None
    tool_bus: ToolBus | None = None
    model_router: ModelRouter | None = None

    def resolved_control_plane(self) -> ControlPlane:
        if self.control_plane is None:
            self.control_plane = FileBackedControlPlane()
        return self.control_plane

    def resolved_model_router(self) -> ModelRouter:
        if self.model_router is not None:
            return self.model_router
        config_path = Path("configs") / "openeinstein.example.yaml"
        if config_path.exists():
            self.model_router = ModelRouter(load_routing_config(config_path))
        else:
            self.model_router = _fallback_router()
        return self.model_router
