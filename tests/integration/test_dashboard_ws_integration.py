"""Dashboard websocket integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openeinstein.gateway.web.app import create_dashboard_app
from openeinstein.gateway.web.config import DashboardConfig, DashboardDeps


def _create_client(tmp_path: Path) -> TestClient:
    static_root = tmp_path / "control-ui"
    static_root.mkdir(parents=True, exist_ok=True)
    (static_root / "index.html").write_text("<html><body>ui</body></html>", encoding="utf-8")
    app = create_dashboard_app(
        config=DashboardConfig(base_path="/", static_dir=static_root),
        deps=DashboardDeps(),
    )
    return TestClient(app)


def _pair_token(client: TestClient) -> str:
    code = client.post("/api/v1/pair/start").json()["code"]
    return client.post("/api/v1/pair/complete", json={"code": code}).json()["token"]


def test_ws_rejects_missing_token(tmp_path: Path) -> None:
    client = _create_client(tmp_path)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/control"):
            pass


def test_ws_connect_sync_and_run_command(tmp_path: Path) -> None:
    client = _create_client(tmp_path)
    token = _pair_token(client)

    with client.websocket_connect(f"/ws/control?token={token}") as ws:
        ws.send_json({"type": "connect", "payload": {"token": token}})
        connected = ws.receive_json()
        assert connected["type"] == "connected"
        assert connected["payload"]["authenticated"] is True

        ws.send_json({"type": "run_command", "payload": {"command": "start"}})
        state = ws.receive_json()
        assert state["type"] == "run_state"
        assert state["payload"]["status"] == "running"

        ws.send_json({"type": "sync_request", "payload": {"last_seq": 0}})
        synced = ws.receive_json()
        assert synced["type"] == "sync_response"
        assert isinstance(synced["payload"]["events"], list)
