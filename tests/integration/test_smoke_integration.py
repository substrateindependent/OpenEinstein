"""Integration smoke checks for cross-subsystem wiring."""

from __future__ import annotations

from openeinstein.cli.main import app
from openeinstein.gateway import load_policy


def test_cli_and_policy_loader_wiring() -> None:
    policy = load_policy("configs/POLICY.json")
    assert policy.enforced_by == "gateway"
    assert callable(app)
