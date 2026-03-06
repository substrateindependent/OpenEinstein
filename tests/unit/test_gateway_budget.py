"""Tests for Gateway-Level Budget Enforcement (Story 4.3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openeinstein.gateway.policy import PolicyConfig, PolicyInvariants
from openeinstein.security.core import (
    ApprovalsStore,
    PolicyEngine,
    PolicyViolationError,
)


def _make_policy(
    *,
    max_total_tokens: int | None = None,
    max_total_cost_usd: float | None = None,
    circuit_breaker_failures: int = 5,
) -> PolicyConfig:
    return PolicyConfig(
        version="1.0",
        enforced_by="gateway",
        note="test policy",
        invariants=PolicyInvariants(
            max_llm_calls_per_step=10,
            max_cas_timeout_minutes=5,
            require_verification_after_gates=False,
            max_total_tokens_per_session=max_total_tokens,
            max_total_cost_per_session_usd=max_total_cost_usd,
            circuit_breaker_consecutive_failures=circuit_breaker_failures,
        ),
    )


@pytest.fixture()
def tmp_approvals(tmp_path: Path) -> ApprovalsStore:
    return ApprovalsStore(tmp_path / "approvals.json")


# --- PolicyInvariants field tests ---


class TestPolicyInvariantsFields:
    def test_new_fields_have_defaults(self) -> None:
        inv = PolicyInvariants(
            max_llm_calls_per_step=10,
            max_cas_timeout_minutes=5,
            require_verification_after_gates=False,
        )
        assert inv.max_total_tokens_per_session is None
        assert inv.max_total_cost_per_session_usd is None
        assert inv.circuit_breaker_consecutive_failures == 5

    def test_explicit_values(self) -> None:
        inv = PolicyInvariants(
            max_llm_calls_per_step=10,
            max_cas_timeout_minutes=5,
            require_verification_after_gates=False,
            max_total_tokens_per_session=500_000,
            max_total_cost_per_session_usd=10.0,
            circuit_breaker_consecutive_failures=3,
        )
        assert inv.max_total_tokens_per_session == 500_000
        assert inv.max_total_cost_per_session_usd == 10.0
        assert inv.circuit_breaker_consecutive_failures == 3

    def test_none_means_unlimited(self) -> None:
        """None budget fields should mean no limit, not zero."""
        policy = _make_policy(max_total_tokens=None, max_total_cost_usd=None)
        assert policy.invariants.max_total_tokens_per_session is None
        assert policy.invariants.max_total_cost_per_session_usd is None

    def test_backward_compatible_json_loading(self, tmp_path: Path) -> None:
        """Old policy JSON without new fields should load with defaults."""
        old_policy = {
            "version": "1.0",
            "enforced_by": "gateway",
            "note": "old",
            "invariants": {
                "max_llm_calls_per_step": 10,
                "max_cas_timeout_minutes": 5,
                "require_verification_after_gates": False,
            },
        }
        p = tmp_path / "POLICY.json"
        p.write_text(json.dumps(old_policy))
        from openeinstein.gateway.policy import load_policy

        config = load_policy(p)
        assert config.invariants.max_total_tokens_per_session is None
        assert config.invariants.circuit_breaker_consecutive_failures == 5


# --- Budget enforcement tests ---


class TestBudgetEnforcement:
    def test_enforce_budget_passes_within_limits(
        self, tmp_approvals: ApprovalsStore
    ) -> None:
        policy = _make_policy(max_total_tokens=10_000, max_total_cost_usd=5.0)
        engine = PolicyEngine(policy, tmp_approvals)
        # Should not raise
        engine.enforce_budget(total_tokens=5000, total_cost_usd=2.5)

    def test_enforce_budget_raises_on_token_breach(
        self, tmp_approvals: ApprovalsStore
    ) -> None:
        policy = _make_policy(max_total_tokens=10_000)
        engine = PolicyEngine(policy, tmp_approvals)
        with pytest.raises(PolicyViolationError, match="token"):
            engine.enforce_budget(total_tokens=15_000, total_cost_usd=0.0)

    def test_enforce_budget_raises_on_cost_breach(
        self, tmp_approvals: ApprovalsStore
    ) -> None:
        policy = _make_policy(max_total_cost_usd=5.0)
        engine = PolicyEngine(policy, tmp_approvals)
        with pytest.raises(PolicyViolationError, match="cost"):
            engine.enforce_budget(total_tokens=0, total_cost_usd=10.0)

    def test_enforce_budget_exact_boundary_passes(
        self, tmp_approvals: ApprovalsStore
    ) -> None:
        """Usage exactly at limit should pass (not breach)."""
        policy = _make_policy(max_total_tokens=10_000, max_total_cost_usd=5.0)
        engine = PolicyEngine(policy, tmp_approvals)
        engine.enforce_budget(total_tokens=10_000, total_cost_usd=5.0)

    def test_enforce_budget_unlimited_when_none(
        self, tmp_approvals: ApprovalsStore
    ) -> None:
        """None limits mean unlimited — should never raise."""
        policy = _make_policy(max_total_tokens=None, max_total_cost_usd=None)
        engine = PolicyEngine(policy, tmp_approvals)
        engine.enforce_budget(total_tokens=999_999_999, total_cost_usd=999_999.0)

    def test_enforce_budget_idempotent(
        self, tmp_approvals: ApprovalsStore
    ) -> None:
        """Calling enforce_budget twice with same values should not double-count."""
        policy = _make_policy(max_total_tokens=10_000)
        engine = PolicyEngine(policy, tmp_approvals)
        # Both calls should pass — enforce_budget is stateless; caller provides totals
        engine.enforce_budget(total_tokens=9000, total_cost_usd=0.0)
        engine.enforce_budget(total_tokens=9000, total_cost_usd=0.0)

    def test_violation_includes_details(
        self, tmp_approvals: ApprovalsStore
    ) -> None:
        """PolicyViolationError should include human-readable budget details."""
        policy = _make_policy(max_total_tokens=10_000)
        engine = PolicyEngine(policy, tmp_approvals)
        with pytest.raises(PolicyViolationError) as exc_info:
            engine.enforce_budget(total_tokens=12_000, total_cost_usd=0.0)
        msg = str(exc_info.value)
        assert "12000" in msg or "12,000" in msg or "12000" in msg
        assert "10000" in msg or "10,000" in msg or "10000" in msg


# --- Integration wiring ---


class TestIntegrationWiring:
    def test_enforce_budget_callable_from_engine(
        self, tmp_approvals: ApprovalsStore
    ) -> None:
        """PolicyEngine has enforce_budget method accessible."""
        policy = _make_policy(max_total_tokens=50_000, max_total_cost_usd=10.0)
        engine = PolicyEngine(policy, tmp_approvals)
        assert hasattr(engine, "enforce_budget")
        engine.enforce_budget(total_tokens=1000, total_cost_usd=0.5)

    def test_policy_violation_is_permission_error(self) -> None:
        """PolicyViolationError is a PermissionError subclass for clean handling."""
        assert issubclass(PolicyViolationError, PermissionError)
