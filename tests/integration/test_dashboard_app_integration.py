"""Integration tests for dashboard app factory and static serving."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from openeinstein.gateway.web.app import create_dashboard_app
from openeinstein.gateway.web.config import DashboardConfig, DashboardDeps


def test_dashboard_app_serves_health_version_and_spa_fallback(tmp_path: Path) -> None:
    static_root = tmp_path / "control-ui"
    static_root.mkdir(parents=True, exist_ok=True)
    (static_root / "index.html").write_text(
        "<!doctype html><html><body><h1>UI</h1></body></html>",
        encoding="utf-8",
    )

    app = create_dashboard_app(
        config=DashboardConfig(base_path="/", static_dir=static_root),
        deps=DashboardDeps(),
    )
    client = TestClient(app)

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    version = client.get("/api/v1/version")
    assert version.status_code == 200
    assert "ui" in version.json()

    index = client.get("/")
    assert index.status_code == 200
    assert "<h1>UI</h1>" in index.text

    fallback = client.get("/runs/run-123")
    assert fallback.status_code == 200
    assert "<h1>UI</h1>" in fallback.text


def test_dashboard_config_uses_packaged_static_assets_by_default() -> None:
    config = DashboardConfig()
    assert config.static_dir.exists()
    assert (config.static_dir / "index.html").exists()
