"""Dashboard web server configuration and dependency container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from openeinstein.gateway.control_plane import ControlPlane, FileBackedControlPlane
from openeinstein.persistence import CampaignDB
from openeinstein.security import ApprovalsStore, PolicyEngine
from openeinstein.tools import ToolBus


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
    static_dir: Path = Path("dist/control-ui")


@dataclass(slots=True)
class DashboardDeps:
    """Dependency container for dashboard route handlers."""

    control_plane: ControlPlane | None = None
    db: CampaignDB | None = None
    approvals_store: ApprovalsStore | None = None
    policy_engine: PolicyEngine | None = None
    tool_bus: ToolBus | None = None

    def resolved_control_plane(self) -> ControlPlane:
        if self.control_plane is None:
            self.control_plane = FileBackedControlPlane()
        return self.control_plane
