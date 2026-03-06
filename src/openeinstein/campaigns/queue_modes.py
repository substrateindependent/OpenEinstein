"""Queue mode handlers for mid-run message handling during concurrent execution.

Each queue mode governs how incoming user/system messages are handled
while a campaign step is actively running in a lane:

- **collect**: Coalesce all pending messages into a single follow-up payload.
- **followup**: Enqueue the message for the next turn without interrupting.
- **steer**: Cancel pending work and inject a new instruction.
"""

from __future__ import annotations

from pydantic import BaseModel

from openeinstein.campaigns.lanes import QueueMode


class QueueAction(BaseModel):
    """Result of processing a mid-run message through a queue mode handler."""

    cancel_pending: bool = False
    inject_instruction: str | None = None
    coalesced_payload: str | None = None
    enqueue_for_next_turn: bool = False
    enqueued_message: str | None = None


class QueueModeHandler:
    """Dispatches mid-run messages to the appropriate queue mode logic."""

    def handle_message(
        self,
        mode: QueueMode,
        pending_messages: list[str],
        new_message: str,
    ) -> QueueAction:
        """Process *new_message* according to *mode*.

        Parameters
        ----------
        mode:
            The queue mode governing how messages are handled.
        pending_messages:
            Messages already queued but not yet processed.
        new_message:
            The newly arrived message.

        Returns
        -------
        QueueAction
            Describes what the executor should do with the message.

        Raises
        ------
        ValueError
            If *mode* is unknown or if *steer* mode receives an empty
            instruction.
        """
        if mode == QueueMode.COLLECT:
            return self._handle_collect(pending_messages, new_message)
        if mode == QueueMode.FOLLOWUP:
            return self._handle_followup(new_message)
        if mode == QueueMode.STEER:
            return self._handle_steer(new_message)
        raise ValueError(f"Unknown queue mode: {mode!r}")

    # ── Private handlers ──

    @staticmethod
    def _handle_collect(
        pending_messages: list[str],
        new_message: str,
    ) -> QueueAction:
        all_msgs = [*pending_messages, new_message]
        # Filter out empty strings
        all_msgs = [m for m in all_msgs if m.strip()]
        if not all_msgs:
            return QueueAction()
        coalesced = "\n---\n".join(all_msgs)
        return QueueAction(coalesced_payload=coalesced)

    @staticmethod
    def _handle_followup(new_message: str) -> QueueAction:
        return QueueAction(
            enqueue_for_next_turn=True,
            enqueued_message=new_message,
        )

    @staticmethod
    def _handle_steer(new_message: str) -> QueueAction:
        if not new_message.strip():
            raise ValueError(
                "Steer mode requires a non-empty instruction to inject"
            )
        return QueueAction(
            cancel_pending=True,
            inject_instruction=new_message,
        )
