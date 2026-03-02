"""Tool status API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from openeinstein.gateway.web.config import DashboardDeps


def build_tools_router(deps: DashboardDeps) -> APIRouter:
    router = APIRouter(prefix="/tools", tags=["tools"])

    @router.get("")
    def list_tools() -> dict[str, list[dict[str, str]]]:
        tool_bus = deps.tool_bus
        if tool_bus is None:
            return {"tools": []}
        servers = sorted(tool_bus.list_servers())
        return {"tools": [{"id": server, "status": "unknown"} for server in servers]}

    @router.get("/{tool_id}")
    def get_tool(tool_id: str) -> dict[str, str]:
        tool_bus = deps.tool_bus
        if tool_bus is None:
            raise HTTPException(status_code=404, detail="Tool bus unavailable")
        if tool_id not in tool_bus.list_servers():
            raise HTTPException(status_code=404, detail="Unknown tool")
        return {"id": tool_id, "status": "available"}

    @router.post("/{tool_id}/test")
    def test_tool(tool_id: str) -> dict[str, str]:
        tool_bus = deps.tool_bus
        if tool_bus is None:
            raise HTTPException(status_code=404, detail="Tool bus unavailable")
        if tool_id not in tool_bus.list_servers():
            raise HTTPException(status_code=404, detail="Unknown tool")
        return {"id": tool_id, "status": "ok"}

    return router
