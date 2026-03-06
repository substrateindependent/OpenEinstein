"""Unit tests for concurrent step tracking (Story 1.4)."""

from __future__ import annotations

import threading

import pytest

from openeinstein.campaigns.state import ConcurrentStepTracker


# ── lane_status: empty when no steps ──


def test_lane_status_empty_when_no_steps() -> None:
    """lane_status returns empty dict when no steps are active (not error)."""
    tracker = ConcurrentStepTracker()
    assert tracker.lane_status == {}


# ── register_step / complete_step lifecycle ──


def test_register_step_adds_to_tracking() -> None:
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    status = tracker.lane_status
    assert "main" in status
    assert status["main"]["active"] == 1
    assert "step-001" in status["main"]["step_ids"]


def test_complete_step_removes_from_tracker() -> None:
    """Step completion removes from tracker (no zombie entries)."""
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    tracker.complete_step("main", "step-001")
    assert tracker.lane_status == {}


def test_multiple_steps_in_different_lanes() -> None:
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "generating")
    tracker.register_step("literature", "step-002", "literature")
    status = tracker.lane_status
    assert status["main"]["active"] == 1
    assert status["literature"]["active"] == 1


def test_complete_one_step_leaves_others() -> None:
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "generating")
    tracker.register_step("literature", "step-002", "literature")
    tracker.complete_step("main", "step-001")
    status = tracker.lane_status
    assert "main" not in status
    assert status["literature"]["active"] == 1


# ── allowed_concurrent_transitions enforcement ──


def test_rejects_duplicate_phase() -> None:
    """Two steps with the same phase cannot run concurrently."""
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    with pytest.raises(ValueError, match="planning"):
        tracker.register_step("main", "step-002", "planning")


def test_rejects_duplicate_phase_different_lanes() -> None:
    """Same-phase rejection applies even across different lanes."""
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "generating")
    with pytest.raises(ValueError, match="generating"):
        tracker.register_step("literature", "step-002", "generating")


def test_allows_concurrent_literature_and_generating() -> None:
    """Literature and generating are in allowed_concurrent_transitions."""
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "generating")
    # Should not raise
    tracker.register_step("literature", "step-002", "literature")
    assert tracker.lane_status["main"]["active"] == 1
    assert tracker.lane_status["literature"]["active"] == 1


def test_allows_concurrent_literature_and_planning() -> None:
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    tracker.register_step("literature", "step-002", "literature")
    assert tracker.lane_status["main"]["active"] == 1
    assert tracker.lane_status["literature"]["active"] == 1


def test_rejects_disallowed_phase_pair() -> None:
    """Phases not in allowed_concurrent_transitions cannot coexist."""
    # planning + generating is not in the default allowed set
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    with pytest.raises(ValueError, match="concurrent"):
        tracker.register_step("main", "step-002", "generating")


def test_allowed_after_previous_completes() -> None:
    """After completing a step, a previously blocked phase can run."""
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    tracker.complete_step("main", "step-001")
    # Should not raise
    tracker.register_step("main", "step-002", "planning")
    assert tracker.lane_status["main"]["active"] == 1


# ── can_run_phase ──


def test_can_run_phase_true_when_empty() -> None:
    tracker = ConcurrentStepTracker()
    assert tracker.can_run_phase("planning") is True


def test_can_run_phase_false_for_duplicate() -> None:
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    assert tracker.can_run_phase("planning") is False


def test_can_run_phase_true_for_allowed_pair() -> None:
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "generating")
    assert tracker.can_run_phase("literature") is True


def test_can_run_phase_false_for_disallowed_pair() -> None:
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    assert tracker.can_run_phase("generating") is False


# ── complete_step edge cases ──


def test_complete_nonexistent_step_noop() -> None:
    """Completing a step not in tracking is a no-op (not error)."""
    tracker = ConcurrentStepTracker()
    tracker.complete_step("main", "step-999")  # Should not raise


def test_complete_step_wrong_lane_noop() -> None:
    """Completing a step in the wrong lane leaves it in original lane."""
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    tracker.complete_step("literature", "step-001")
    assert tracker.lane_status["main"]["active"] == 1


# ── lane_status shape ──


def test_lane_status_contains_step_ids() -> None:
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "generating")
    tracker.register_step("literature", "step-002", "literature")
    status = tracker.lane_status
    assert status["main"]["step_ids"] == {"step-001"}
    assert status["literature"]["step_ids"] == {"step-002"}


# ── allowed_concurrent_transitions is configurable ──


def test_custom_allowed_transitions() -> None:
    """Tracker accepts custom allowed transitions."""
    custom = frozenset({frozenset({"planning", "generating"})})
    tracker = ConcurrentStepTracker(allowed_concurrent=custom)
    tracker.register_step("main", "step-001", "planning")
    # Now planning+generating is allowed
    tracker.register_step("main", "step-002", "generating")
    assert tracker.lane_status["main"]["active"] == 2


def test_custom_allowed_rejects_unlisted_pair() -> None:
    """Custom transitions reject pairs not listed."""
    custom = frozenset({frozenset({"planning", "generating"})})
    tracker = ConcurrentStepTracker(allowed_concurrent=custom)
    tracker.register_step("main", "step-001", "planning")
    with pytest.raises(ValueError, match="concurrent"):
        tracker.register_step("literature", "step-002", "literature")


# ── Thread safety ──


def test_tracker_thread_safe_complete() -> None:
    """Concurrent complete calls don't corrupt tracker state."""
    tracker = ConcurrentStepTracker()
    tracker.register_step("main", "step-001", "planning")
    errors: list[str] = []

    def try_complete(idx: int) -> None:
        try:
            tracker.complete_step("main", "step-001")
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=try_complete, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert tracker.lane_status == {}


# ── Import smoke test ──


def test_concurrent_step_tracker_importable() -> None:
    from openeinstein.campaigns.state import ConcurrentStepTracker

    assert ConcurrentStepTracker is not None
