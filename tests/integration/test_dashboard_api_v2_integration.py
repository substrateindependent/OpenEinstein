"""Integration tests for the `/api/v2/*` runtime cutover surface."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from openeinstein.gateway.control_plane import FileBackedControlPlane
from openeinstein.gateway.runtime_control import ExecutorBackedControlPlane
from openeinstein.gateway.web.app import create_dashboard_app
from openeinstein.gateway.web.config import DashboardConfig, DashboardDeps


def _client(tmp_path: Path, *, seed_legacy_run: bool = False) -> tuple[TestClient, str | None]:
    control_plane_root = tmp_path / ".openeinstein" / "control-plane"
    legacy_run_id: str | None = None
    if seed_legacy_run:
        legacy = FileBackedControlPlane(control_plane_root)
        legacy_run_id = legacy.start_run("run-legacy")
        legacy.emit_event(legacy_run_id, "legacy_seeded", {"source": "integration-test"})

    static_root = tmp_path / "control-ui"
    static_root.mkdir(parents=True, exist_ok=True)
    (static_root / "index.html").write_text("<html><body>ui</body></html>", encoding="utf-8")

    app = create_dashboard_app(
        config=DashboardConfig(base_path="/", static_dir=static_root),
        deps=DashboardDeps(
            control_plane=ExecutorBackedControlPlane(
                control_plane_root,
                tmp_path / ".openeinstein" / "openeinstein.db",
            )
        ),
    )
    return TestClient(app), legacy_run_id


def _pair_token(client: TestClient) -> str:
    code = client.post("/api/v2/pair/start").json()["code"]
    token = client.post("/api/v2/pair/complete", json={"code": code}).json()["token"]
    assert token
    return token


def test_v2_health_version_and_runs_contract(tmp_path: Path) -> None:
    client, _legacy_run_id = _client(tmp_path)

    health = client.get("/api/v2/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    version = client.get("/api/v2/version")
    assert version.status_code == 200
    assert version.json()["protocol"] == "v2"

    token = _pair_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    campaign = tmp_path / "campaign.yaml"
    campaign.write_text(
        "\n".join(
            [
                "campaign:",
                "  name: v2-campaign",
                "  version: '0.1.0'",
                "  search_space:",
                "    generator_skill: v2-skill",
                "  gate_pipeline:",
                "    - name: v2-gate",
                "      skill: v2-gate-skill",
                "      timeout_seconds: 5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    started = client.post("/api/v2/runs", json={"campaign_path": str(campaign)}, headers=headers)
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    listed = client.get("/api/v2/runs", headers=headers)
    assert listed.status_code == 200
    assert any(run["run_id"] == run_id for run in listed.json()["runs"])

    events = client.get(f"/api/v2/runs/{run_id}/events", headers=headers)
    assert events.status_code == 200
    assert isinstance(events.json()["events"], list)


def test_v1_legacy_run_stop_and_compare_do_not_500(tmp_path: Path) -> None:
    client, legacy_run_id = _client(tmp_path, seed_legacy_run=True)
    assert legacy_run_id is not None

    token = _pair_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    stopped = client.post(f"/api/v1/runs/{legacy_run_id}/stop", headers=headers)
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"

    compared = client.get(
        f"/api/v1/runs/compare?run_ids={legacy_run_id},run-missing",
        headers=headers,
    )
    assert compared.status_code == 200
    payload = compared.json()
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["run_id"] == legacy_run_id
    assert "run-missing" in payload["missing_run_ids"]
