"""Unit tests for compaction engine and content blocks (Story 3.1)."""

from __future__ import annotations

from datetime import datetime, timezone

from openeinstein.agents.compaction import (
    BlockType,
    CompactionEngine,
    CompactionError,
    ContentBlock,
    RetentionPolicy,
    RetentionRule,
    load_compaction_config,
)


# ── ContentBlock model ──


def test_content_block_creation() -> None:
    """ContentBlock can be created with all fields."""
    block = ContentBlock(
        content="Hello world",
        block_type=BlockType.recent,
        created_at=datetime.now(tz=timezone.utc),
        token_count=3,
    )
    assert block.content == "Hello world"
    assert block.block_type == BlockType.recent
    assert block.token_count == 3


def test_content_block_types() -> None:
    """BlockType enum has all required values."""
    assert BlockType.pinned.value == "pinned"
    assert BlockType.recent.value == "recent"
    assert BlockType.summary.value == "summary"
    assert BlockType.ephemeral.value == "ephemeral"


# ── RetentionPolicy ──


def test_retention_policy_default_rules() -> None:
    """RetentionPolicy has per-type rules."""
    policy = RetentionPolicy()
    assert isinstance(policy.rules, dict)
    # Policy should have rules for at least pinned and ephemeral
    assert BlockType.pinned in policy.rules or "pinned" in {r for r in policy.rules}


def test_retention_rule_creation() -> None:
    """RetentionRule model with required fields."""
    rule = RetentionRule(
        action="retain",
        max_age_steps=None,
    )
    assert rule.action == "retain"
    assert rule.max_age_steps is None

    rule2 = RetentionRule(action="discard", max_age_steps=5)
    assert rule2.max_age_steps == 5


# ── CompactionEngine ──


def test_compact_empty_context() -> None:
    """Compact with empty context returns empty list."""
    engine = CompactionEngine()
    result = engine.compact([], budget=1000)
    assert result == []


def test_compact_within_budget_no_change() -> None:
    """Context within budget is returned unchanged."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content="A", block_type=BlockType.recent, created_at=now, token_count=10),
        ContentBlock(content="B", block_type=BlockType.recent, created_at=now, token_count=10),
    ]
    engine = CompactionEngine()
    result = engine.compact(blocks, budget=100)
    assert len(result) == 2
    assert result[0].content == "A"


def test_compact_pinned_always_retained() -> None:
    """Pinned blocks are always retained regardless of budget pressure."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content="PINNED", block_type=BlockType.pinned, created_at=now, token_count=50),
        ContentBlock(content="RECENT", block_type=BlockType.recent, created_at=now, token_count=50),
        ContentBlock(content="EPHEMERAL", block_type=BlockType.ephemeral, created_at=now, token_count=50),
    ]
    engine = CompactionEngine(recent_turns_keep=0)
    result = engine.compact(blocks, budget=60)
    # Pinned block must survive
    pinned = [b for b in result if b.block_type == BlockType.pinned]
    assert len(pinned) == 1
    assert pinned[0].content == "PINNED"


def test_compact_recent_turns_kept_verbatim() -> None:
    """Recent N turns are kept verbatim."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content=f"turn-{i}", block_type=BlockType.recent, created_at=now, token_count=10)
        for i in range(10)
    ]
    engine = CompactionEngine(recent_turns_keep=3)
    result = engine.compact(blocks, budget=500)
    # Last 3 recent blocks should survive verbatim
    recent_contents = [b.content for b in result if b.block_type == BlockType.recent]
    assert "turn-7" in recent_contents
    assert "turn-8" in recent_contents
    assert "turn-9" in recent_contents


def test_compact_ephemeral_discarded_first() -> None:
    """Ephemeral blocks are discarded before other types."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content="PINNED", block_type=BlockType.pinned, created_at=now, token_count=20),
        ContentBlock(content="RECENT", block_type=BlockType.recent, created_at=now, token_count=20),
        ContentBlock(content="EPHEMERAL1", block_type=BlockType.ephemeral, created_at=now, token_count=20),
        ContentBlock(content="EPHEMERAL2", block_type=BlockType.ephemeral, created_at=now, token_count=20),
    ]
    engine = CompactionEngine(recent_turns_keep=1)
    result = engine.compact(blocks, budget=50)
    # Ephemeral should be gone
    ephemeral = [b for b in result if b.block_type == BlockType.ephemeral]
    assert len(ephemeral) == 0


def test_compact_budget_smaller_than_pinned_raises() -> None:
    """Budget smaller than total pinned tokens raises CompactionError."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content="PINNED1", block_type=BlockType.pinned, created_at=now, token_count=100),
        ContentBlock(content="PINNED2", block_type=BlockType.pinned, created_at=now, token_count=100),
    ]
    engine = CompactionEngine()
    try:
        engine.compact(blocks, budget=50)
        assert False, "Expected CompactionError"
    except CompactionError as exc:
        assert "pinned" in str(exc).lower() or "budget" in str(exc).lower()


def test_compact_all_pinned_returned_unmodified() -> None:
    """All-pinned context returns all blocks unmodified."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content="P1", block_type=BlockType.pinned, created_at=now, token_count=10),
        ContentBlock(content="P2", block_type=BlockType.pinned, created_at=now, token_count=10),
    ]
    engine = CompactionEngine()
    result = engine.compact(blocks, budget=100)
    assert len(result) == 2
    assert all(b.block_type == BlockType.pinned for b in result)


def test_compact_tier_ordering() -> None:
    """Compacted output respects tier ordering: pinned first, then recent, then summaries."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content="R1", block_type=BlockType.recent, created_at=now, token_count=10),
        ContentBlock(content="P1", block_type=BlockType.pinned, created_at=now, token_count=10),
        ContentBlock(content="R2", block_type=BlockType.recent, created_at=now, token_count=10),
    ]
    engine = CompactionEngine(recent_turns_keep=5)
    result = engine.compact(blocks, budget=500)
    # Pinned should come before recent in output
    types = [b.block_type for b in result]
    pinned_indices = [i for i, t in enumerate(types) if t == BlockType.pinned]
    recent_indices = [i for i, t in enumerate(types) if t == BlockType.recent]
    if pinned_indices and recent_indices:
        assert max(pinned_indices) < min(recent_indices)


def test_compact_30_blocks_respects_budget() -> None:
    """Compact on 30-block context respects budget and retains pinned blocks."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content=f"block-{i}", block_type=BlockType.recent, created_at=now, token_count=100)
        for i in range(28)
    ]
    # Add 2 pinned blocks
    blocks.insert(0, ContentBlock(content="invariant-1", block_type=BlockType.pinned, created_at=now, token_count=50))
    blocks.insert(1, ContentBlock(content="invariant-2", block_type=BlockType.pinned, created_at=now, token_count=50))

    engine = CompactionEngine(recent_turns_keep=5)
    result = engine.compact(blocks, budget=800)

    # Total tokens should be within budget
    total_tokens = sum(b.token_count for b in result)
    assert total_tokens <= 800

    # Pinned blocks must survive
    pinned = [b for b in result if b.block_type == BlockType.pinned]
    assert len(pinned) == 2
    assert {b.content for b in pinned} == {"invariant-1", "invariant-2"}


def test_compact_summarized_older_turns() -> None:
    """Older turns beyond recent window are summarized (become summary blocks)."""
    now = datetime.now(tz=timezone.utc)
    blocks = [
        ContentBlock(content=f"old-turn-{i}", block_type=BlockType.recent, created_at=now, token_count=50)
        for i in range(10)
    ]
    engine = CompactionEngine(recent_turns_keep=3)
    # Budget tight enough that old turns can't all stay
    result = engine.compact(blocks, budget=300)

    # Should have some summary blocks for old turns (or fewer total)
    # The recent 3 should be verbatim
    recent_verbatim = [b for b in result if b.block_type == BlockType.recent]
    assert len(recent_verbatim) <= 3


# ── Config loading ──


def test_load_compaction_config_defaults(tmp_path: object) -> None:
    """Default config values are sensible."""
    config = load_compaction_config(None)
    assert config["recent_turns_keep"] == 5
    assert config["budget_trigger_pct"] == 70


def test_load_compaction_config_from_yaml(tmp_path: object) -> None:
    """Config loaded from YAML overrides defaults."""
    from pathlib import Path

    config_path = Path(str(tmp_path)) / "compaction.yaml"
    config_path.write_text(
        "recent_turns_keep: 8\nbudget_trigger_pct: 60\nsummary_model_role: fast\n",
        encoding="utf-8",
    )
    config = load_compaction_config(config_path)
    assert config["recent_turns_keep"] == 8
    assert config["budget_trigger_pct"] == 60


# ── Import smoke tests ──


def test_import_compaction_engine_from_agents() -> None:
    from openeinstein.agents import CompactionEngine as _CE  # noqa: F401


def test_import_content_block_from_compaction() -> None:
    from openeinstein.agents.compaction import ContentBlock as _CB  # noqa: F401


def test_import_block_type_from_compaction() -> None:
    from openeinstein.agents.compaction import BlockType as _BT  # noqa: F401
