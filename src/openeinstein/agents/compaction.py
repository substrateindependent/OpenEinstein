"""Tiered context compaction engine with content block models."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from openeinstein.gateway.hooks import HookRegistry

_logger = logging.getLogger(__name__)


class BlockType(str, Enum):
    """Content block retention tier."""

    pinned = "pinned"
    recent = "recent"
    summary = "summary"
    ephemeral = "ephemeral"


class ContentBlock(BaseModel):
    """A typed content block with retention metadata."""

    content: str
    block_type: BlockType
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    token_count: int = 0


class RetentionRule(BaseModel):
    """Per-type retention rule."""

    action: str = "retain"  # retain | summarize | discard
    max_age_steps: int | None = None


class RetentionPolicy(BaseModel):
    """Retention rules keyed by block type."""

    rules: dict[BlockType, RetentionRule] = Field(default_factory=lambda: {
        BlockType.pinned: RetentionRule(action="retain"),
        BlockType.recent: RetentionRule(action="retain"),
        BlockType.summary: RetentionRule(action="retain"),
        BlockType.ephemeral: RetentionRule(action="discard", max_age_steps=0),
    })


class CompactionError(Exception):
    """Raised when compaction cannot satisfy constraints."""


class CompactionEngine:
    """Implements 4-tier compaction strategy for context management.

    Tier 1: Pinned blocks always retained.
    Tier 2: Recent N turns kept verbatim.
    Tier 3: Older turns summarized (converted to summary blocks).
    Tier 4: Ephemeral/ancient turns discarded.
    """

    def __init__(
        self,
        *,
        recent_turns_keep: int = 5,
        retention_policy: RetentionPolicy | None = None,
        hook_registry: HookRegistry | None = None,
    ) -> None:
        self._recent_turns_keep = recent_turns_keep
        self._policy = retention_policy or RetentionPolicy()
        self._hook_registry = hook_registry

    def compact(self, context: list[ContentBlock], budget: int) -> list[ContentBlock]:
        """Compact context blocks to fit within token budget.

        Args:
            context: Ordered list of content blocks.
            budget: Maximum total tokens allowed in output.

        Returns:
            Compacted list of content blocks.

        Raises:
            CompactionError: If pinned blocks alone exceed budget.
        """
        if not context:
            return []

        total_tokens_before = sum(b.token_count for b in context)
        self._dispatch_hook(
            "before_compaction",
            {"total_tokens_before": total_tokens_before, "block_count": len(context), "budget": budget},
        )

        result = self._compact_inner(context, budget)

        total_tokens_after = sum(b.token_count for b in result)
        self._dispatch_hook(
            "after_compaction",
            {
                "total_tokens_before": total_tokens_before,
                "total_tokens_after": total_tokens_after,
                "block_count_before": len(context),
                "block_count_after": len(result),
            },
        )

        return result

    def _dispatch_hook(self, hook_point: str, payload: dict) -> None:  # type: ignore[type-arg]
        """Dispatch a hook if registry is configured. Errors are logged, not raised."""
        if self._hook_registry is None:
            return
        try:
            from openeinstein.gateway.hooks import HookContext

            ctx = HookContext(hook_point=hook_point, payload=payload)  # type: ignore[arg-type]
            self._hook_registry.dispatch(hook_point, ctx)  # type: ignore[arg-type]
        except Exception:
            _logger.exception("Compaction hook dispatch error for %s", hook_point)

    def _compact_inner(self, context: list[ContentBlock], budget: int) -> list[ContentBlock]:
        """Core compaction logic."""

        # Tier 1: Separate pinned blocks (always retained)
        pinned = [b for b in context if b.block_type == BlockType.pinned]
        pinned_tokens = sum(b.token_count for b in pinned)

        if pinned_tokens > budget:
            raise CompactionError(
                f"Pinned blocks require {pinned_tokens} tokens but budget is {budget}. "
                "Cannot compact without losing pinned context."
            )

        # Check if everything fits
        total = sum(b.token_count for b in context)
        if total <= budget:
            # Reorder: pinned first, then rest in original order
            non_pinned = [b for b in context if b.block_type != BlockType.pinned]
            return pinned + non_pinned

        # Tier 4: Discard ephemeral blocks first
        non_ephemeral = [b for b in context if b.block_type not in (BlockType.pinned, BlockType.ephemeral)]

        # Tier 2: Keep recent N turns verbatim
        recent_blocks = [b for b in non_ephemeral if b.block_type == BlockType.recent]
        other_blocks = [b for b in non_ephemeral if b.block_type != BlockType.recent]

        # Split recent into kept (last N) and older
        if len(recent_blocks) > self._recent_turns_keep:
            older_recent = recent_blocks[: len(recent_blocks) - self._recent_turns_keep]
            kept_recent = recent_blocks[len(recent_blocks) - self._recent_turns_keep:]
        else:
            older_recent = []
            kept_recent = list(recent_blocks)

        remaining_budget = budget - pinned_tokens
        recent_tokens = sum(b.token_count for b in kept_recent)

        if recent_tokens > remaining_budget:
            # Trim recent to fit
            trimmed_recent: list[ContentBlock] = []
            used = 0
            for block in reversed(kept_recent):
                if used + block.token_count <= remaining_budget:
                    trimmed_recent.insert(0, block)
                    used += block.token_count
                else:
                    break
            return pinned + trimmed_recent

        remaining_budget -= recent_tokens

        # Tier 3: Summarize older turns if there's budget left
        result_other: list[ContentBlock] = []
        if older_recent or other_blocks:
            combined_older = older_recent + other_blocks
            if combined_older:
                # Create a single summary block from older content
                summary_content = "; ".join(
                    b.content[:50] for b in combined_older
                )
                summary_tokens = min(
                    remaining_budget,
                    max(10, sum(b.token_count for b in combined_older) // 4),
                )
                if summary_tokens > 0 and remaining_budget >= 10:
                    result_other.append(
                        ContentBlock(
                            content=summary_content[:summary_tokens * 4],
                            block_type=BlockType.summary,
                            token_count=summary_tokens,
                        )
                    )

        return pinned + result_other + kept_recent


def load_compaction_config(path: Path | None) -> dict[str, int | str]:
    """Load compaction configuration from YAML or return defaults."""
    defaults: dict[str, int | str] = {
        "recent_turns_keep": 5,
        "summary_model_role": "fast",
        "budget_trigger_pct": 70,
    }
    if path is None or not path.exists():
        return defaults

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return defaults

    for key in defaults:
        if key in data:
            defaults[key] = data[key]

    return defaults
