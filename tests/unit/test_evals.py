"""Unit tests for eval framework scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from openeinstein.evals import EvalRunner, discover_eval_suites
from openeinstein.persistence import CampaignDB


def _write_suite(path: Path) -> None:
    path.write_text(
        """
eval_suite:
  name: trivial-suite
  description: trivial two case suite
  cases:
    - name: case-one
      input:
        value: 1
      expected:
        result: 2
    - name: case-two
      input:
        value: 2
      expected:
        result: 3
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_eval_runner_loads_and_runs_two_case_suite(tmp_path: Path) -> None:
    suite_path = tmp_path / "trivial.yaml"
    _write_suite(suite_path)

    db = CampaignDB(tmp_path / "evals.db")
    runner = EvalRunner(db, executor=lambda payload: {"result": int(payload["value"]) + 1})

    suite = runner.load_suite(suite_path)
    report = runner.run_suite(suite, run_id="eval-run-1")

    assert suite.name == "trivial-suite"
    assert report.total_cases == 2
    assert report.passed_cases == 2
    assert report.failed_cases == 0
    stored = db.get_eval_results("eval-run-1")
    assert len(stored) == 2
    assert all(result.passed for result in stored)
    db.close()


def test_discover_eval_suites_and_validation(tmp_path: Path) -> None:
    suite_dir = tmp_path / "evals"
    suite_dir.mkdir()
    _write_suite(suite_dir / "a.yaml")
    _write_suite(suite_dir / "b.yml")
    discovered = discover_eval_suites(suite_dir)
    assert [path.name for path in discovered] == ["a.yaml", "b.yml"]

    broken_path = suite_dir / "broken.yaml"
    broken_path.write_text("eval_suite:\n  name: broken\n  cases: bad\n", encoding="utf-8")
    db = CampaignDB(tmp_path / "validation.db")
    runner = EvalRunner(db)
    with pytest.raises(ValidationError):
        runner.load_suite(broken_path)
    db.close()
