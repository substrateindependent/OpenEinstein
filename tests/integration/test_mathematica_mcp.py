"""Integration tests for Mathematica MCP server."""

from __future__ import annotations

from pathlib import Path

from conftest import requires_wolfram
from openeinstein.tools import MCPConnectionManager, MathematicaMCPServer, ToolBus


@requires_wolfram
def test_mathematica_server_lifecycle_xact_timeout_recovery(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("mathematica", MathematicaMCPServer(tmp_path / "mathematica"))
    bus = ToolBus(manager)

    created = bus.call("mathematica", "create_session", {"session_name": "default"})
    assert created.success
    session_id = created.output["session_id"]

    evaluated = bus.call(
        "mathematica",
        "evaluate",
        {"session_id": session_id, "expression": "1+1", "timeout_seconds": 10},
    )
    if not evaluated.success and evaluated.error and "not activated" in evaluated.error.lower():
        import pytest

        pytest.skip("Wolfram Engine not activated")
    assert evaluated.success
    assert evaluated.output["result"] == "2"

    loaded = bus.call("mathematica", "load_xact", {"session_id": session_id})
    if not loaded.success and loaded.error and "not activated" in loaded.error.lower():
        import pytest

        pytest.skip("Wolfram Engine not activated")
    assert loaded.success
    assert loaded.output["loaded"] is True

    timed_out = bus.call(
        "mathematica",
        "evaluate",
        {"session_id": session_id, "expression": "Pause[2];1", "timeout_seconds": 0.1},
    )
    assert timed_out.success is False

    recovered = bus.call("mathematica", "recover_kernel", {"session_id": session_id})
    assert recovered.success
    assert recovered.output["recovered"] is True

    evaluated_again = bus.call(
        "mathematica",
        "evaluate",
        {"session_id": session_id, "expression": "2+2", "timeout_seconds": 20},
    )
    if (
        not evaluated_again.success
        and evaluated_again.error
        and "not activated" in evaluated_again.error.lower()
    ):
        import pytest

        pytest.skip("Wolfram Engine not activated")
    assert evaluated_again.success
    assert evaluated_again.output["result"] == "4"

    closed = bus.call("mathematica", "close_session", {"session_id": session_id})
    assert closed.success
