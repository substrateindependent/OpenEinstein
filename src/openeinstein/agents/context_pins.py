"""Context pin registry for durable context blocks (Story 3.2)."""

from __future__ import annotations

from openeinstein.agents.compaction import BlockType, ContentBlock
from openeinstein.persistence.db import CampaignDB, ContextPinRecord


class ContextPinRegistry:
    """Manages durable context pins backed by SQLite persistence.

    Pins are context blocks that survive compaction — they are always
    retained at the top of the compacted context window.
    """

    def __init__(self, db: CampaignDB) -> None:
        self._db = db

    def pin(
        self,
        run_id: str,
        content: str,
        reason: str,
        block_type: str = "pinned",
    ) -> int:
        """Pin a content block for durable retention."""
        return self._db.add_context_pin(
            run_id=run_id,
            block_type=block_type,
            content=content,
            reason=reason,
        )

    def unpin(self, pin_id: int) -> None:
        """Remove a pin by ID. No-op if pin doesn't exist."""
        self._db.remove_context_pin(pin_id)

    def list_pins(self, run_id: str) -> list[ContextPinRecord]:
        """List all pins for a given run."""
        return self._db.get_context_pins(run_id)

    def as_content_blocks(self, run_id: str) -> list[ContentBlock]:
        """Return pins as ContentBlock objects for compaction integration."""
        pins = self._db.get_context_pins(run_id)
        return [
            ContentBlock(
                content=pin.content,
                block_type=BlockType.pinned,
                token_count=len(pin.content.split()),
            )
            for pin in pins
        ]
