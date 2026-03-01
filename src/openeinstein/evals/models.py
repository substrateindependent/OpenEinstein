"""Typed schemas for eval suites and results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """Single deterministic eval case."""

    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)


class EvalSuite(BaseModel):
    """Collection of eval cases."""

    name: str
    description: str | None = None
    cases: list[EvalCase] = Field(default_factory=list)


class EvalSuiteDocument(BaseModel):
    """YAML document wrapper."""

    eval_suite: EvalSuite


class EvalCaseResult(BaseModel):
    """Per-case execution output."""

    case_name: str
    passed: bool
    expected: dict[str, Any]
    actual: dict[str, Any]


class EvalRunReport(BaseModel):
    """Summary report for an eval suite run."""

    run_id: str
    suite_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_results: list[EvalCaseResult] = Field(default_factory=list)
