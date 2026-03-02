"""Integration test for dashboard CLI entrypoint wiring."""

from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

from openeinstein.cli.main import app


def test_dashboard_command_invokes_uvicorn_and_browser(monkeypatch) -> None:
    runner = CliRunner()
    called: dict[str, Any] = {}

    def fake_uvicorn_run(target_app: Any, host: str, port: int, log_level: str) -> None:
        called["app"] = target_app
        called["host"] = host
        called["port"] = port
        called["log_level"] = log_level

    def fake_open(url: str) -> bool:
        called["opened_url"] = url
        return True

    monkeypatch.setattr("openeinstein.cli.main.uvicorn.run", fake_uvicorn_run)
    monkeypatch.setattr("openeinstein.cli.main.webbrowser.open", fake_open)

    result = runner.invoke(app, ["dashboard", "--port", "8420"])
    assert result.exit_code == 0
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 8420
    assert called["opened_url"] == "http://127.0.0.1:8420/"
