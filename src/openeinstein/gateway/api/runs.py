"""Run lifecycle API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from openeinstein.gateway.events import EventHub
from openeinstein.gateway.web.config import DashboardDeps


class StartRunRequest(BaseModel):
    campaign_path: str | None = None
    parameters: dict[str, Any] | None = None


def build_runs_router(deps: DashboardDeps, event_hub: EventHub) -> APIRouter:
    router = APIRouter(prefix="/runs", tags=["runs"])
    control = deps.resolved_control_plane()

    @router.get("")
    def list_runs() -> dict[str, Any]:
        return {"runs": [record.model_dump() for record in control.list_runs()]}

    @router.post("")
    def start_run(payload: StartRunRequest) -> dict[str, Any]:
        run_id = control.start_run()
        if payload.campaign_path:
            control.emit_event(run_id, "campaign_path_set", {"campaign_path": payload.campaign_path})
        event_hub.publish("run_state", {"run_id": run_id, "status": "running"})
        return {"run_id": run_id, "status": control.get_status(run_id)}

    @router.get("/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            record = control.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return record.model_dump()

    @router.post("/{run_id}/pause")
    def pause_run(run_id: str) -> dict[str, Any]:
        control.stop_run(run_id, reason="paused")
        event_hub.publish("run_state", {"run_id": run_id, "status": "stopped"})
        return {"run_id": run_id, "status": control.get_status(run_id)}

    @router.post("/{run_id}/resume")
    def resume_run(run_id: str) -> dict[str, Any]:
        control.resume_run(run_id)
        event_hub.publish("run_state", {"run_id": run_id, "status": "running"})
        return {"run_id": run_id, "status": control.get_status(run_id)}

    @router.post("/{run_id}/stop")
    def stop_run(run_id: str) -> dict[str, Any]:
        control.stop_run(run_id, reason="stopped")
        event_hub.publish("run_state", {"run_id": run_id, "status": "stopped"})
        return {"run_id": run_id, "status": control.get_status(run_id)}

    @router.get("/{run_id}/events")
    def run_events(run_id: str, after_seq: int = 0, limit: int = 100) -> dict[str, Any]:
        events = control.get_events(run_id)
        filtered = [event.model_dump() for event in events][after_seq : after_seq + limit]
        return {"events": filtered}

    @router.get("/{run_id}/cost")
    def run_cost(run_id: str) -> dict[str, Any]:
        control.get_run(run_id)
        return {
            "run_id": run_id,
            "estimated_cost_usd": 0.0,
            "token_count": 0,
            "budget_percent": 0.0,
        }

    @router.post("/{run_id}/export")
    def export_run(run_id: str) -> dict[str, Any]:
        control.get_run(run_id)
        export_root = Path(".openeinstein") / "exports"
        export_root.mkdir(parents=True, exist_ok=True)
        export_file = export_root / f"{run_id}-paper-pack.zip"
        export_file.write_bytes(b"")
        control.attach_artifact(run_id, "Paper Pack", export_file)
        event_hub.publish("run_event", {"run_id": run_id, "event": "paper_pack_exported"})
        return {"run_id": run_id, "download_url": f"/api/v1/artifacts/{export_file.name}/download"}

    return router
