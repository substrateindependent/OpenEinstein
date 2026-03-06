"""Unit tests for queue mode handlers (Story 1.2)."""

from __future__ import annotations

import pytest

from openeinstein.campaigns.queue_modes import (
    QueueAction,
    QueueModeHandler,
)
from openeinstein.campaigns.lanes import QueueMode


# ── QueueAction model tests ──


def test_queue_action_noop() -> None:
    action = QueueAction()
    assert action.cancel_pending is False
    assert action.inject_instruction is None
    assert action.coalesced_payload is None


def test_queue_action_steer_fields() -> None:
    action = QueueAction(
        cancel_pending=True,
        inject_instruction="Switch to new hypothesis.",
    )
    assert action.cancel_pending is True
    assert action.inject_instruction == "Switch to new hypothesis."


# ── Collect mode tests ──


def test_collect_coalesces_messages() -> None:
    handler = QueueModeHandler()
    pending = ["First message", "Second message"]
    new = "Third message"
    action = handler.handle_message(QueueMode.COLLECT, pending, new)
    assert action.cancel_pending is False
    assert action.inject_instruction is None
    assert action.coalesced_payload is not None
    # All three messages should be in the coalesced payload
    assert "First message" in action.coalesced_payload
    assert "Second message" in action.coalesced_payload
    assert "Third message" in action.coalesced_payload


def test_collect_single_message() -> None:
    handler = QueueModeHandler()
    action = handler.handle_message(QueueMode.COLLECT, [], "Only message")
    assert action.coalesced_payload is not None
    assert "Only message" in action.coalesced_payload


def test_collect_zero_messages_noop() -> None:
    """Collect with empty pending and empty new returns no-op."""
    handler = QueueModeHandler()
    action = handler.handle_message(QueueMode.COLLECT, [], "")
    assert action.cancel_pending is False
    assert action.coalesced_payload is None


# ── Followup mode tests ──


def test_followup_enqueues_message() -> None:
    handler = QueueModeHandler()
    action = handler.handle_message(QueueMode.FOLLOWUP, ["old"], "new instruction")
    assert action.cancel_pending is False
    assert action.inject_instruction is None
    assert action.enqueue_for_next_turn is True
    assert action.enqueued_message == "new instruction"


def test_followup_preserves_pending() -> None:
    """Followup doesn't touch pending messages."""
    handler = QueueModeHandler()
    pending = ["a", "b"]
    action = handler.handle_message(QueueMode.FOLLOWUP, pending, "c")
    assert action.cancel_pending is False


# ── Steer mode tests ──


def test_steer_cancels_and_injects() -> None:
    handler = QueueModeHandler()
    action = handler.handle_message(
        QueueMode.STEER, ["old"], "New direction"
    )
    assert action.cancel_pending is True
    assert action.inject_instruction == "New direction"


def test_steer_empty_instruction_raises() -> None:
    handler = QueueModeHandler()
    with pytest.raises(ValueError, match="instruction"):
        handler.handle_message(QueueMode.STEER, [], "")


def test_steer_whitespace_only_instruction_raises() -> None:
    handler = QueueModeHandler()
    with pytest.raises(ValueError, match="instruction"):
        handler.handle_message(QueueMode.STEER, [], "   ")


# ── Unknown mode test ──


def test_unknown_mode_raises() -> None:
    handler = QueueModeHandler()
    with pytest.raises(ValueError, match="Unknown queue mode"):
        handler.handle_message("invalid_mode", [], "msg")  # type: ignore[arg-type]


# ── Import smoke test ──


def test_queue_mode_handler_importable() -> None:
    from openeinstein.campaigns import QueueModeHandler

    assert QueueModeHandler is not None
