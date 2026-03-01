"""Unit checks for known-model truth table coverage."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]


MODEL_OUTCOMES = {
    "general_relativity": True,
    "lambda_cdm": True,
    "toy_ghost_model": False,
    "toy_tachyon_model": False,
    "horndeski_safe_slice": True,
}


def test_known_models_suite_matches_truth_table_keys() -> None:
    suite_path = Path(
        "campaign-packs/modified-gravity-action-search/evals/known-models.yaml"
    )
    payload = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    cases = payload["eval_suite"]["cases"]
    suite_models = {case["input"]["model"] for case in cases}
    assert suite_models == set(MODEL_OUTCOMES)
