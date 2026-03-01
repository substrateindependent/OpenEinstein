"""Eval suite loading and deterministic execution."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable

import yaml  # type: ignore[import-untyped]

from openeinstein.evals.models import (
    EvalCaseResult,
    EvalRunReport,
    EvalSuite,
    EvalSuiteDocument,
)
from openeinstein.persistence import CampaignDB

EvalExecutor = Callable[[dict[str, Any]], dict[str, Any]]


class EvalRunner:
    """Runs eval suites and persists case outcomes."""

    def __init__(self, db: CampaignDB, executor: EvalExecutor | None = None) -> None:
        self._db = db
        self._executor = executor or (lambda payload: payload)

    def load_suite(self, path: str | Path) -> EvalSuite:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        doc = EvalSuiteDocument.model_validate(payload)
        return doc.eval_suite

    def run_suite(
        self,
        suite: EvalSuite,
        run_id: str | None = None,
        executor: EvalExecutor | None = None,
    ) -> EvalRunReport:
        execution_run_id = run_id or f"eval-{uuid.uuid4().hex[:10]}"
        run_executor = executor or self._executor
        case_results: list[EvalCaseResult] = []

        for case in suite.cases:
            actual = run_executor(case.input)
            passed = actual == case.expected
            self._db.add_eval_result(
                run_id=execution_run_id,
                suite_name=suite.name,
                case_name=case.name,
                passed=passed,
                expected=case.expected,
                actual=actual,
            )
            case_results.append(
                EvalCaseResult(
                    case_name=case.name,
                    passed=passed,
                    expected=case.expected,
                    actual=actual,
                )
            )

        passed_cases = sum(1 for result in case_results if result.passed)
        return EvalRunReport(
            run_id=execution_run_id,
            suite_name=suite.name,
            total_cases=len(case_results),
            passed_cases=passed_cases,
            failed_cases=len(case_results) - passed_cases,
            case_results=case_results,
        )


def discover_eval_suites(root: str | Path) -> list[Path]:
    """Discover YAML suite files from a directory."""

    root_path = Path(root)
    if not root_path.exists():
        return []
    return sorted(
        [*root_path.rglob("*.yaml"), *root_path.rglob("*.yml")],
        key=lambda item: str(item),
    )
