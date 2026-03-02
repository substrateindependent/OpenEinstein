"""Run lifecycle API routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from openeinstein.gateway.events import EventHub
from openeinstein.gateway.web.config import DashboardDeps


class StartRunRequest(BaseModel):
    campaign_path: str | None = None
    parameters: dict[str, Any] | None = None


class ForkRunRequest(BaseModel):
    event_index: int = 0


class RunTagsRequest(BaseModel):
    tags: list[str]


def build_runs_router(deps: DashboardDeps, event_hub: EventHub) -> APIRouter:
    router = APIRouter(prefix="/runs", tags=["runs"])
    control = deps.resolved_control_plane()
    tags_path = Path(".openeinstein") / "run-tags.json"

    def load_tags() -> dict[str, list[str]]:
        if not tags_path.exists():
            return {}
        return json.loads(tags_path.read_text(encoding="utf-8"))

    def save_tags(tags: dict[str, list[str]]) -> None:
        tags_path.parent.mkdir(parents=True, exist_ok=True)
        tags_path.write_text(json.dumps(tags, indent=2), encoding="utf-8")

    @router.get("/compare")
    def compare_runs(run_ids: str) -> dict[str, list[dict[str, Any]]]:
        requested = [item.strip() for item in run_ids.split(",") if item.strip()]
        tag_map = load_tags()
        compared: list[dict[str, Any]] = []
        for run_id in requested:
            record = control.get_run(run_id)
            estimated_cost = 0.0
            for event in control.get_events(run_id):
                estimated_cost = float(event.payload.get("estimated_cost_usd", estimated_cost))
            confidence = {
                "failed": 0.30,
                "running": 0.72,
                "stopped": 0.55,
                "completed": 0.90,
            }.get(record.status, 0.50)
            compared.append(
                {
                    "run_id": record.run_id,
                    "status": record.status,
                    "estimated_cost_usd": estimated_cost,
                    "confidence": confidence,
                    "tags": tag_map.get(record.run_id, []),
                }
            )
        return {"runs": compared}

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

    @router.post("/{run_id}/tags")
    def update_run_tags(run_id: str, payload: RunTagsRequest) -> dict[str, Any]:
        control.get_run(run_id)
        tags = load_tags()
        tags[run_id] = payload.tags
        save_tags(tags)
        return {"run_id": run_id, "tags": payload.tags}

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

    @router.post("/{run_id}/fork")
    def fork_run(run_id: str, payload: ForkRunRequest) -> dict[str, Any]:
        control.get_run(run_id)
        forked_run_id = control.start_run()
        control.emit_event(
            forked_run_id,
            "forked_from",
            {"parent_run_id": run_id, "event_index": payload.event_index},
        )
        event_hub.publish(
            "run_state",
            {
                "run_id": forked_run_id,
                "status": control.get_status(forked_run_id),
                "parent_run_id": run_id,
            },
        )
        return {
            "run_id": forked_run_id,
            "status": control.get_status(forked_run_id),
            "parent_run_id": run_id,
        }

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
