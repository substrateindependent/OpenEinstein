"""Runtime ToolBus initialization from OpenEinstein config."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from openeinstein.tools.ads_server import ADSMCPServer
from openeinstein.tools.arxiv_server import ArxivMCPServer
from openeinstein.tools.crossref_server import CrossrefMCPServer
from openeinstein.tools.grobid_server import GrobidMCPServer
from openeinstein.tools.inspire_server import InspireMCPServer
from openeinstein.tools.python_sandbox_server import PythonSandboxMCPServer
from openeinstein.tools.registry_server import CampaignRegistryServer
from openeinstein.tools.scanner_server import ScannerMCPServer
from openeinstein.tools.semantic_scholar_server import SemanticScholarMCPServer
from openeinstein.tools.sympy_server import SympyMCPServer
from openeinstein.tools.tool_bus import MCPConnectionManager, ToolBus, load_tool_servers_from_yaml
from openeinstein.tools.types import ToolServer, ToolSpec
from openeinstein.tools.zotero_server import ZoteroMCPServer


class ToolRuntimeServerStatus(BaseModel):
    server: str
    required: bool
    available: bool
    reason: str = ""


class ToolRuntimeInitReport(BaseModel):
    servers: list[ToolRuntimeServerStatus] = Field(default_factory=list)

    @property
    def missing_required(self) -> list[str]:
        return [item.server for item in self.servers if item.required and not item.available]


class UnavailableToolServer:
    """Non-operational server placeholder used for optional/missing plugins."""

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def start(self) -> None:  # pragma: no cover - no-op
        return

    def stop(self) -> None:  # pragma: no cover - no-op
        return

    def health_check(self) -> bool:
        return False

    def list_tools(self) -> list[ToolSpec]:
        return []

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:  # noqa: ARG002
        raise RuntimeError(self._reason)



def initialize_tool_bus_from_config(
    config_path: str | Path = Path("configs") / "openeinstein.example.yaml",
    *,
    workspace_root: str | Path = Path(".openeinstein"),
    db_path: str | Path = Path(".openeinstein") / "openeinstein.db",
) -> tuple[ToolBus, ToolRuntimeInitReport]:
    root = Path(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    config_file = Path(config_path)

    manager = MCPConnectionManager()
    report = ToolRuntimeInitReport()

    if config_file.exists():
        servers = load_tool_servers_from_yaml(config_file)
    else:
        servers = {
            "registry": {"required": True},
            "sympy": {"required": True},
            "scanner": {"required": True},
            "python_sandbox": {"required": True},
        }
    for server_name, raw in sorted(servers.items()):
        required = bool(raw.get("required", False)) if isinstance(raw, dict) else False
        try:
            server = _server_from_name(server_name, root=root, db_path=Path(db_path))
            manager.register_server(server_name, server)
            report.servers.append(
                ToolRuntimeServerStatus(
                    server=server_name,
                    required=required,
                    available=True,
                    reason="",
                )
            )
        except Exception as exc:  # noqa: BLE001
            manager.register_server(server_name, UnavailableToolServer(str(exc)))
            report.servers.append(
                ToolRuntimeServerStatus(
                    server=server_name,
                    required=required,
                    available=False,
                    reason=str(exc),
                )
            )

    return ToolBus(manager), report



def _server_from_name(server_name: str, *, root: Path, db_path: Path) -> ToolServer:
    key = server_name.lower()
    if key == "registry":
        return CampaignRegistryServer(db_path)
    if key == "sympy":
        return SympyMCPServer(root / "sympy")
    if key == "scanner":
        return ScannerMCPServer(root / "scanner")
    if key == "python_sandbox":
        return PythonSandboxMCPServer(root / "python-sandbox")
    if key == "arxiv":
        return ArxivMCPServer(root / "arxiv")
    if key in {"semantic_scholar", "semantic-scholar"}:
        return SemanticScholarMCPServer(root / "semantic-scholar")
    if key in {"inspire", "inspire-hep"}:
        return InspireMCPServer(root / "inspire")
    if key in {"ads", "nasa_ads", "nasa-ads"}:
        return ADSMCPServer(root / "ads")
    if key == "crossref":
        return CrossrefMCPServer(root / "crossref")
    if key == "zotero":
        return ZoteroMCPServer(root / "zotero")
    if key == "grobid":
        return GrobidMCPServer(root / "grobid")

    raise ValueError(f"No runtime initializer for tool server '{server_name}'")
