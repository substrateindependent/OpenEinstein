"""Integration tests for scanner MCP server."""

from __future__ import annotations

from pathlib import Path

from openeinstein.tools import MCPConnectionManager, ScannerMCPServer, ToolBus


def test_scanner_server_known_function_viable_region(tmp_path: Path) -> None:
    manager = MCPConnectionManager()
    manager.register_server("scanner", ScannerMCPServer(tmp_path / "scans"))
    bus = ToolBus(manager)

    grid = bus.call(
        "scanner",
        "scan_grid",
        {
            "expression": "x**2 + y**2",
            "x_min": -2.0,
            "x_max": 2.0,
            "y_min": -2.0,
            "y_max": 2.0,
            "steps": 31,
            "threshold": 1.0,
        },
    )
    assert grid.success
    assert grid.output["viable_points"] > 0
    assert Path(grid.output["plot_path"]).exists()

    adaptive = bus.call(
        "scanner",
        "scan_adaptive",
        {
            "expression": "x**2 + y**2",
            "x_min": -2.0,
            "x_max": 2.0,
            "y_min": -2.0,
            "y_max": 2.0,
            "initial_steps": 9,
            "refine_steps": 21,
            "threshold": 1.0,
            "top_k": 3,
        },
    )
    assert adaptive.success
    assert adaptive.output["viable_points"] > 0
    assert Path(adaptive.output["plot_path"]).exists()

    boundary = bus.call(
        "scanner",
        "find_boundary",
        {
            "expression": "x**2 + y**2",
            "x_min": -2.0,
            "x_max": 2.0,
            "y_value": 0.0,
            "steps": 400,
            "threshold": 1.0,
        },
    )
    assert boundary.success
    assert boundary.output["count"] >= 2
    boundaries = boundary.output["boundaries"]
    assert any(abs(value - 1.0) < 0.1 for value in boundaries)
    assert any(abs(value + 1.0) < 0.1 for value in boundaries)
