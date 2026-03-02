"""Natural-language intent routing endpoints for dashboard commands."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from openeinstein.gateway.web.config import DashboardDeps
from openeinstein.routing.models import ModelRole


class IntentRequest(BaseModel):
    command: str = Field(min_length=1)


def _resolve_navigation(command: str) -> tuple[str, str]:
    lowered = command.lower()
    if "approval" in lowered:
        return "navigate", "/approvals"
    if "artifact" in lowered:
        return "navigate", "/artifacts"
    if "compare" in lowered:
        return "navigate", "/compare"
    if "tool" in lowered:
        return "navigate", "/tools"
    if "setting" in lowered:
        return "navigate", "/settings"
    if "builder" in lowered:
        return "navigate", "/builder"
    if "market" in lowered:
        return "navigate", "/marketplace"
    if "layout" in lowered:
        return "navigate", "/layout"
    return "navigate", "/"


def build_intent_router(deps: DashboardDeps) -> APIRouter:
    router = APIRouter(prefix="/intent", tags=["intent"])

    @router.post("/command")
    def resolve_command(payload: IntentRequest) -> dict[str, Any]:
        command = payload.command.strip()
        role: ModelRole = "fast"
        model_router = deps.resolved_model_router()
        resolved_model = model_router.resolve(role).model_dump(mode="json")
        control = deps.resolved_control_plane()

        if re.search(r"\b(start|launch)\s+run\b", command, flags=re.IGNORECASE):
            run_id = control.start_run()
            return {
                "action": "start_run",
                "route": "/",
                "message": f"Started run {run_id}",
                "run_id": run_id,
                "resolved_role": role,
                "resolved_model": resolved_model,
                "toolbus_used": False,
            }

        match = re.search(r"test tool (?P<tool>[a-zA-Z0-9_-]+)", command, flags=re.IGNORECASE)
        if match is not None and deps.tool_bus is not None:
            tool_id = match.group("tool")
            if tool_id in deps.tool_bus.list_servers():
                specs = deps.tool_bus.get_tools(tool_id)
                if specs:
                    outcome = deps.tool_bus.call(tool_id, specs[0].name, {})
                    return {
                        "action": "test_tool",
                        "route": "/tools",
                        "message": f"Tool {tool_id} test status: {'ok' if outcome.success else 'failed'}",
                        "resolved_role": role,
                        "resolved_model": resolved_model,
                        "toolbus_used": True,
                    }
            return {
                "action": "test_tool",
                "route": "/tools",
                "message": f"Tool {tool_id} is unavailable",
                "resolved_role": role,
                "resolved_model": resolved_model,
                "toolbus_used": True,
            }

        action, route = _resolve_navigation(command)
        return {
            "action": action,
            "route": route,
            "message": f"Navigating to {route}",
            "resolved_role": role,
            "resolved_model": resolved_model,
            "toolbus_used": False,
        }

    return router
