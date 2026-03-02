"""Dashboard API integration tests for auth and run lifecycle wiring."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from openeinstein.gateway.control_plane import FileBackedControlPlane
from openeinstein.gateway.web.app import create_dashboard_app
from openeinstein.gateway.web.config import DashboardConfig, DashboardDeps
from openeinstein.security import ApprovalsStore


def _client(tmp_path: Path) -> TestClient:
    static_root = tmp_path / "control-ui"
    static_root.mkdir(parents=True, exist_ok=True)
    (static_root / "index.html").write_text("<html><body>ui</body></html>", encoding="utf-8")
    app = create_dashboard_app(
        config=DashboardConfig(base_path="/", static_dir=static_root),
        deps=DashboardDeps(
            control_plane=FileBackedControlPlane(tmp_path / ".openeinstein" / "control-plane"),
            approvals_store=ApprovalsStore(tmp_path / ".openeinstein" / "approvals.json"),
        ),
    )
    return TestClient(app)


def _pair_and_get_token(client: TestClient) -> str:
    started = client.post("/api/v1/pair/start")
    assert started.status_code == 200
    code = started.json()["code"]
    completed = client.post("/api/v1/pair/complete", json={"code": code})
    assert completed.status_code == 200
    token = completed.json()["token"]
    assert isinstance(token, str) and token
    return token


def test_run_endpoints_require_auth_and_support_lifecycle(tmp_path: Path) -> None:
    client = _client(tmp_path)

    unauthorized = client.get("/api/v1/runs")
    assert unauthorized.status_code == 401

    token = _pair_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    started = client.post("/api/v1/runs", json={"campaign_path": "campaigns/sample.yaml"}, headers=headers)
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    listed = client.get("/api/v1/runs", headers=headers)
    assert listed.status_code == 200
    assert any(run["run_id"] == run_id for run in listed.json()["runs"])

    run = client.get(f"/api/v1/runs/{run_id}", headers=headers)
    assert run.status_code == 200
    assert run.json()["run_id"] == run_id

    paused = client.post(f"/api/v1/runs/{run_id}/pause", headers=headers)
    assert paused.status_code == 200
    resumed = client.post(f"/api/v1/runs/{run_id}/resume", headers=headers)
    assert resumed.status_code == 200
    stopped = client.post(f"/api/v1/runs/{run_id}/stop", headers=headers)
    assert stopped.status_code == 200

    events = client.get(f"/api/v1/runs/{run_id}/events", headers=headers)
    assert events.status_code == 200
    assert len(events.json()["events"]) >= 1

    exported = client.post(f"/api/v1/runs/{run_id}/export", headers=headers)
    assert exported.status_code == 200
    artifact_name = exported.json()["download_url"].split("/")[-2]
    download = client.get(f"/api/v1/artifacts/{artifact_name}/download", headers=headers)
    assert download.status_code == 200
    preview = client.get(f"/api/v1/artifacts/{artifact_name}/preview", headers=headers)
    assert preview.status_code == 200
    listed_artifacts = client.get(f"/api/v1/runs/{run_id}/artifacts", headers=headers)
    assert listed_artifacts.status_code == 200
    assert len(listed_artifacts.json()["artifacts"]) >= 1


def test_approval_endpoints_are_wired_and_mutate_store(tmp_path: Path) -> None:
    client = _client(tmp_path)
    token = _pair_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    listed = client.get("/api/v1/approvals", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["approvals"] == []

    decided = client.post(
        "/api/v1/approvals/approval-shell/decide",
        json={"action": "shell_exec", "decision": "approve"},
        headers=headers,
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"

    bulk = client.post(
        "/api/v1/approvals/bulk",
        json={
            "approvals": [
                {"action": "tool.read", "decision": "approve"},
                {"action": "shell_exec", "decision": "deny"},
            ]
        },
        headers=headers,
    )
    assert bulk.status_code == 200
    assert bulk.json()["processed"] == 2

    listed_after = client.get("/api/v1/approvals", headers=headers)
    assert listed_after.status_code == 200
    approvals = listed_after.json()["approvals"]
    assert any(item["action"] == "tool.read" for item in approvals)
