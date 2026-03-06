"""Tests for Circuit Breaker for Model Router (Story 4.4)."""

from __future__ import annotations

import threading
import time

import pytest

from openeinstein.routing.models import (
    ModelConfig,
    RoleConfig,
    RoutingConfig,
    RoutingRoles,
    RoutingRoot,
)
from openeinstein.routing.router import CircuitBreaker, ModelRouter


def _make_config() -> RoutingConfig:
    """Create a minimal routing config for testing."""
    mc = ModelConfig(provider="test", model="test-model")
    role_cfg = RoleConfig(description="test role", default=mc)
    return RoutingConfig(
        model_routing=RoutingRoot(
            roles=RoutingRoles(
                reasoning=role_cfg,
                generation=role_cfg,
                fast=role_cfg,
                embeddings=role_cfg,
            )
        )
    )


# --- CircuitBreaker standalone tests ---


class TestCircuitBreaker:
    def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10.0)
        assert cb.is_closed("reasoning")

    def test_opens_after_threshold_failures(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10.0)
        for _ in range(3):
            cb.record_failure("reasoning")
        assert not cb.is_closed("reasoning")

    def test_success_resets_failures(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10.0)
        cb.record_failure("reasoning")
        cb.record_failure("reasoning")
        cb.record_success("reasoning")
        assert cb.is_closed("reasoning")
        # After reset, need 3 more failures to open
        cb.record_failure("reasoning")
        assert cb.is_closed("reasoning")

    def test_per_role_isolation(self) -> None:
        """Failure in one role doesn't affect another."""
        cb = CircuitBreaker(threshold=2, cooldown_seconds=10.0)
        cb.record_failure("reasoning")
        cb.record_failure("reasoning")
        assert not cb.is_closed("reasoning")
        assert cb.is_closed("fast")

    def test_cooldown_recovery(self) -> None:
        """After cooldown, breaker allows a retry."""
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0.1)
        cb.record_failure("reasoning")
        assert not cb.is_closed("reasoning")
        time.sleep(0.15)
        assert cb.is_closed("reasoning")

    def test_zero_cooldown_never_auto_recovers(self) -> None:
        """Cooldown of 0 means breaker stays open until manual reset."""
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0.0)
        cb.record_failure("reasoning")
        assert not cb.is_closed("reasoning")
        time.sleep(0.05)
        assert not cb.is_closed("reasoning")

    def test_manual_reset(self) -> None:
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0.0)
        cb.record_failure("fast")
        assert not cb.is_closed("fast")
        cb.reset("fast")
        assert cb.is_closed("fast")

    def test_check_raises_when_open(self) -> None:
        cb = CircuitBreaker(threshold=1, cooldown_seconds=10.0)
        cb.record_failure("reasoning")
        with pytest.raises(RuntimeError, match="[Cc]ircuit breaker"):
            cb.check("reasoning")

    def test_check_passes_when_closed(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10.0)
        cb.check("reasoning")  # Should not raise

    def test_thread_safety(self) -> None:
        """Concurrent record_failure calls don't corrupt state."""
        cb = CircuitBreaker(threshold=100, cooldown_seconds=10.0)
        errors: list[Exception] = []

        def _fail_many() -> None:
            try:
                for _ in range(50):
                    cb.record_failure("reasoning")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_fail_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # Should have opened (200 > 100)
        assert not cb.is_closed("reasoning")


# --- ModelRouter integration with circuit breaker ---


class TestRouterCircuitBreakerIntegration:
    def test_router_with_circuit_breaker(self) -> None:
        """run_with_fallback checks breaker state."""
        config = _make_config()
        cb = CircuitBreaker(threshold=2, cooldown_seconds=10.0)
        router = ModelRouter(config, circuit_breaker=cb)

        # Simulate failures by calling directly
        cb.record_failure("reasoning")
        cb.record_failure("reasoning")

        with pytest.raises(RuntimeError, match="[Cc]ircuit breaker"):
            router.run_with_fallback("reasoning", lambda mc: "result")

    def test_router_without_circuit_breaker(self) -> None:
        """Router works normally without circuit breaker (backward compatible)."""
        config = _make_config()
        router = ModelRouter(config)
        result = router.run_with_fallback("reasoning", lambda mc: "ok")
        assert result == "ok"

    def test_success_resets_breaker_through_router(self) -> None:
        """Successful call via router resets the breaker."""
        config = _make_config()
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10.0)
        router = ModelRouter(config, circuit_breaker=cb)

        # Record some failures
        cb.record_failure("fast")
        cb.record_failure("fast")

        # Successful call should reset
        router.run_with_fallback("fast", lambda mc: "ok")
        assert cb.is_closed("fast")

    def test_failure_records_in_breaker_through_router(self) -> None:
        """Failed call via router records failure in breaker."""
        config = _make_config()
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10.0)
        router = ModelRouter(config, circuit_breaker=cb)

        with pytest.raises(RuntimeError):
            router.run_with_fallback("generation", lambda mc: (_ for _ in ()).throw(ValueError("boom")))

        # One failure recorded (one provider in chain)
        assert cb.is_closed("generation")  # threshold 3, only 1 failure

    def test_cooldown_allows_retry_through_router(self) -> None:
        """After cooldown, router can try again."""
        config = _make_config()
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0.1)
        router = ModelRouter(config, circuit_breaker=cb)

        # Trip the breaker
        cb.record_failure("fast")

        # Should be open
        with pytest.raises(RuntimeError, match="[Cc]ircuit breaker"):
            router.run_with_fallback("fast", lambda mc: "ok")

        # Wait for cooldown
        time.sleep(0.15)

        # Should work now
        result = router.run_with_fallback("fast", lambda mc: "recovered")
        assert result == "recovered"
