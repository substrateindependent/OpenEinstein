"""Repository bootstrap smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import openeinstein


def test_package_version_present() -> None:
    assert openeinstein.__version__


def test_policy_json_is_valid() -> None:
    policy_path = Path("configs/POLICY.json")
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    assert data["enforced_by"] == "gateway"
