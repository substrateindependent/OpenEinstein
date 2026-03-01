"""Integration test for known-model mini-campaign truth table."""

from __future__ import annotations

from pathlib import Path

from openeinstein.evals import EvalRunner
from openeinstein.persistence import CampaignDB


MODEL_OUTCOMES = {
    "general_relativity": True,
    "lambda_cdm": True,
    "toy_ghost_model": False,
    "toy_tachyon_model": False,
    "horndeski_safe_slice": True,
}


def _mini_campaign_executor(payload: dict[str, object]) -> dict[str, object]:
    model = str(payload.get("model", ""))
    return {"viable": MODEL_OUTCOMES[model]}


def test_known_models_mini_campaign_zero_false_pos_neg(tmp_path: Path) -> None:
    db = CampaignDB(tmp_path / ".openeinstein" / "openeinstein.db")
    runner = EvalRunner(db, executor=_mini_campaign_executor)
    suite = runner.load_suite(
        Path("campaign-packs/modified-gravity-action-search/evals/known-models.yaml")
    )
    report = runner.run_suite(suite, run_id="known-model-mini")

    assert report.total_cases >= 5
    assert report.failed_cases == 0

    false_positive = 0
    false_negative = 0
    for case in report.case_results:
        expected = bool(case.expected["viable"])
        actual = bool(case.actual["viable"])
        if actual and not expected:
            false_positive += 1
        if expected and not actual:
            false_negative += 1

    assert false_positive == 0
    assert false_negative == 0
    db.close()
