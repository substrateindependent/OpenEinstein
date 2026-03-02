"""Validation tests for UI epic contract completeness."""

from __future__ import annotations

import re
from pathlib import Path


EPIC_PATH = Path(__file__).resolve().parents[2] / "docs" / "epics" / "EPIC-001-control-ui.md"
EXPECTED_ICS = [f"IC-{index:02d}" for index in range(1, 23)]


def _contract_rows(markdown: str) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    pattern = re.compile(
        r"^\|\s*(IC-\d{2})\s*\|\s*[^|]+\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
        re.MULTILINE,
    )
    for contract_id, runtime_path, integration_test in pattern.findall(markdown):
        rows[contract_id] = (runtime_path.strip(), integration_test.strip())
    return rows


def test_ui_epic_document_exists() -> None:
    assert EPIC_PATH.exists(), f"Expected epic document at {EPIC_PATH}"


def test_ui_epic_declares_all_integration_contracts() -> None:
    markdown = EPIC_PATH.read_text(encoding="utf-8")
    rows = _contract_rows(markdown)
    missing = [contract_id for contract_id in EXPECTED_ICS if contract_id not in rows]
    assert not missing, f"Missing integration contracts in epic doc: {missing}"


def test_ui_epic_contracts_define_runtime_and_test_wiring() -> None:
    markdown = EPIC_PATH.read_text(encoding="utf-8")
    rows = _contract_rows(markdown)
    assert rows, "No integration contract rows found in epic markdown table"
    for contract_id in EXPECTED_ICS:
        runtime_path, integration_test = rows[contract_id]
        assert runtime_path and "TBD" not in runtime_path, (
            f"{contract_id} must define a concrete runtime path"
        )
        assert integration_test and "TBD" not in integration_test, (
            f"{contract_id} must define a concrete integration test id"
        )

