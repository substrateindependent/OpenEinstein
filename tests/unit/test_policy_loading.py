"""Policy loading tests for gateway machine-enforced invariants."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.gateway import PolicyConfig, PolicyLoadError, load_policy


def test_policy_json_loads_and_validates() -> None:
    policy = load_policy(Path("configs/POLICY.json"))
    assert isinstance(policy, PolicyConfig)
    assert policy.enforced_by == "gateway"
    assert "shell_exec" in policy.invariants.require_approval_for


def test_invalid_policy_raises_validation_error(tmp_path: Path) -> None:
    invalid_policy = tmp_path / "invalid-policy.json"
    invalid_policy.write_text('{"version":"1.0","enforced_by":"gateway"}', encoding="utf-8")

    with pytest.raises(PolicyLoadError):
        load_policy(invalid_policy)


def test_malformed_policy_json_raises_error(tmp_path: Path) -> None:
    malformed_policy = tmp_path / "malformed-policy.json"
    malformed_policy.write_text("{not-json", encoding="utf-8")

    with pytest.raises(PolicyLoadError):
        load_policy(malformed_policy)

