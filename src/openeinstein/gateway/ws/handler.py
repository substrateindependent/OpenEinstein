"""Websocket route registration for dashboard control UI."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from openeinstein.gateway.auth import DashboardAuthService
from openeinstein.gateway.events import EventHub
from openeinstein.gateway.web.config import DashboardConfig, DashboardDeps
from openeinstein.gateway.ws.protocol import WSClientMessage


def _normalize_base_path(base_path: str) -> str:
    if not base_path or base_path == "/":
        return ""
    return "/" + base_path.strip("/")


def _ws_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": event_type, "payload": payload}


def register_ws_routes(
    app: FastAPI,
    *,
    config: DashboardConfig,
    deps: DashboardDeps,
    auth_service: DashboardAuthService,
    event_hub: EventHub,
) -> None:
    """Attach websocket control endpoint to the app."""

    ws_path = f"{_normalize_base_path(config.base_path)}/ws/control" or "/ws/control"

    @app.websocket(ws_path)
    async def ws_control(websocket: WebSocket) -> None:
        query_token = websocket.query_params.get("token")
        if query_token is None or not auth_service.validate_token(query_token):
            await websocket.close(code=4401)
            return

        await websocket.accept()
        try:
            initial_raw = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        except TimeoutError:
            await websocket.close(code=4401)
            return

        initial = WSClientMessage.model_validate(initial_raw)
        if initial.type != "connect":
            await websocket.close(code=4401)
            return
        token = str(initial.payload.get("token", ""))
        if token != query_token or not auth_service.validate_token(token):
            await websocket.close(code=4401)
            return

        await websocket.send_json(
            _ws_payload(
                "connected",
                {
                    "authenticated": True,
                    "capabilities": ["runs", "approvals", "artifacts", "tools"],
                },
            )
        )
        event_hub.publish("connected", {"authenticated": True})

        control = deps.resolved_control_plane()
        verbosity = "normal"

        try:
            while True:
                try:
                    raw_message = await asyncio.wait_for(websocket.receive_json(), timeout=15.0)
                except TimeoutError:
                    await websocket.send_json(event_hub.heartbeat().model_dump())
                    continue

                message = WSClientMessage.model_validate(raw_message)

                if message.type == "connect":
                    await websocket.send_json(
                        _ws_payload("connected", {"authenticated": True, "verbosity": verbosity})
                    )
                    continue

                if message.type == "sync_request":
                    last_seq = int(message.payload.get("last_seq", 0))
                    events = [event.model_dump() for event in event_hub.sync_after(last_seq)]
                    await websocket.send_json(_ws_payload("sync_response", {"events": events}))
                    continue

                if message.type == "set_verbosity":
                    verbosity = str(message.payload.get("level", "normal"))
                    await websocket.send_json(
                        _ws_payload("run_event", {"event": "verbosity_updated", "level": verbosity})
                    )
                    continue

                if message.type == "approval_decision":
                    await websocket.send_json(
                        _ws_payload("approval_resolved", {"status": "recorded", **message.payload})
                    )
                    continue

                if message.type == "run_command":
                    command = str(message.payload.get("command", "")).lower()
                    run_id = message.payload.get("run_id")
                    if command == "start":
                        run_id = control.start_run()
                    elif run_id is None:
                        run_id = control.latest_run_id()
                    if not run_id:
                        await websocket.send_json(
                            _ws_payload("error", {"classification": "blocking", "message": "No run selected"})
                        )
                        continue
                    if command == "pause":
                        control.stop_run(run_id, reason="paused from websocket")
                    elif command == "resume":
                        control.resume_run(run_id)
                    elif command == "stop":
                        control.stop_run(run_id, reason="stopped from websocket")

                    await websocket.send_json(
                        _ws_payload(
                            "run_state",
                            {
                                "run_id": run_id,
                                "status": control.get_status(run_id),
                                "verbosity": verbosity,
                            },
                        )
                    )
                    continue

        except WebSocketDisconnect:
            return
