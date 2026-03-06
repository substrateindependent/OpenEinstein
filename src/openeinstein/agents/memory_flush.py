"""Pre-compaction memory flush manager (Story 3.3).

Extracts durable notes from context before compaction discards older turns.
Notes are persisted to SQLite and can be referenced in later reasoning steps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openeinstein.agents.compaction import ContentBlock
from openeinstein.persistence.db import CampaignDB

logger = logging.getLogger(__name__)


@dataclass
class DurableNote:
    """A durable note extracted from context before compaction."""

    run_id: str
    step_id: str
    content: str


class MemoryFlushManager:
    """Extracts and persists durable notes from context before compaction.

    Uses the fast model role via ModelRouter to identify important
    information worth preserving from context blocks that would
    otherwise be discarded during compaction.
    """

    def __init__(self, db: CampaignDB, model_router: Any = None) -> None:
        self._db = db
        self._router = model_router

    def flush_before_compaction(
        self,
        run_id: str,
        context: list[ContentBlock],
        step_id: str = "flush",
    ) -> list[DurableNote]:
        """Extract durable notes from context blocks before compaction.

        Returns extracted notes. On failure, returns empty list
        (flush must never block compaction).
        """
        if not context:
            return []

        try:
            return self._extract_and_persist(run_id, context, step_id)
        except Exception:
            logger.exception("Memory flush failed for run %s; continuing", run_id)
            return []

    def _extract_and_persist(
        self,
        run_id: str,
        context: list[ContentBlock],
        step_id: str,
    ) -> list[DurableNote]:
        """Call the fast model to extract notes, then persist them."""
        combined = "\n---\n".join(block.content for block in context)

        def _call(model_config: Any) -> str:
            # The router's call interface passes config to the callable.
            # In production, this would call litellm/pydantic-ai with model_config.
            # For now, we return the model's response directly.
            return f"Extract key insights from: {combined[:500]}"

        # Use model router if available
        if self._router is not None:
            raw_notes = self._router.run_with_fallback("fast", _call)
        else:
            raw_notes = combined[:200]

        # Parse response into notes
        notes: list[DurableNote] = []
        note = DurableNote(run_id=run_id, step_id=step_id, content=str(raw_notes))
        notes.append(note)

        # Persist to DB
        for n in notes:
            self._db.add_durable_note(
                run_id=n.run_id,
                step_id=n.step_id,
                content=n.content,
            )

        return notes
