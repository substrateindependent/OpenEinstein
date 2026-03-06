"""Unit tests for context pin registry and persistence (Story 3.2)."""

from __future__ import annotations

from pathlib import Path

from openeinstein.agents.compaction import BlockType, CompactionEngine, ContentBlock
from openeinstein.agents.context_pins import ContextPinRegistry
from openeinstein.persistence.db import CampaignDB


# ── CampaignDB context_pins CRUD ──


def test_db_add_pin_and_get_pins(tmp_path: Path) -> None:
    """add_pin inserts and get_pins retrieves."""
    db = CampaignDB(tmp_path / "test.db")
    pin_id = db.add_context_pin(
        run_id="run-1",
        block_type="pinned",
        content="Safety invariant: no hallucination",
        reason="safety",
    )
    assert pin_id > 0

    pins = db.get_context_pins("run-1")
    assert len(pins) == 1
    assert pins[0].content == "Safety invariant: no hallucination"
    assert pins[0].reason == "safety"
    db.close()


def test_db_get_pins_empty(tmp_path: Path) -> None:
    """get_pins with no pins returns empty list."""
    db = CampaignDB(tmp_path / "test.db")
    pins = db.get_context_pins("nonexistent")
    assert pins == []
    db.close()


def test_db_remove_pin(tmp_path: Path) -> None:
    """remove_pin deletes a specific pin."""
    db = CampaignDB(tmp_path / "test.db")
    pin_id = db.add_context_pin(
        run_id="run-1",
        block_type="pinned",
        content="To be removed",
        reason="test",
    )
    db.remove_context_pin(pin_id)
    pins = db.get_context_pins("run-1")
    assert len(pins) == 0
    db.close()


def test_db_remove_nonexistent_pin_is_noop(tmp_path: Path) -> None:
    """Removing a non-existent pin does not raise."""
    db = CampaignDB(tmp_path / "test.db")
    db.remove_context_pin(99999)  # Should not raise
    db.close()


def test_db_pins_survive_reconnect(tmp_path: Path) -> None:
    """Pins persist after closing and reopening DB."""
    db_path = tmp_path / "test.db"
    db = CampaignDB(db_path)
    db.add_context_pin(
        run_id="run-1",
        block_type="pinned",
        content="Durable pin",
        reason="durability",
    )
    db.close()

    # Reopen
    db2 = CampaignDB(db_path)
    pins = db2.get_context_pins("run-1")
    assert len(pins) == 1
    assert pins[0].content == "Durable pin"
    db2.close()


def test_db_multiple_pins_per_run(tmp_path: Path) -> None:
    """Multiple pins for the same run_id all persist."""
    db = CampaignDB(tmp_path / "test.db")
    db.add_context_pin(run_id="run-1", block_type="pinned", content="Pin A", reason="a")
    db.add_context_pin(run_id="run-1", block_type="pinned", content="Pin B", reason="b")
    db.add_context_pin(run_id="run-2", block_type="pinned", content="Pin C", reason="c")

    pins_1 = db.get_context_pins("run-1")
    pins_2 = db.get_context_pins("run-2")
    assert len(pins_1) == 2
    assert len(pins_2) == 1
    db.close()


# ── ContextPinRegistry ──


def test_pin_and_list(tmp_path: Path) -> None:
    """pin() adds an entry, list_pins() retrieves it."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)

    registry.pin(run_id="run-1", content="Invariant X", reason="safety")
    pins = registry.list_pins("run-1")
    assert len(pins) == 1
    assert pins[0].content == "Invariant X"
    db.close()


def test_unpin(tmp_path: Path) -> None:
    """unpin() removes a pin by ID."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)

    registry.pin(run_id="run-1", content="To remove", reason="test")
    pins = registry.list_pins("run-1")
    assert len(pins) == 1
    pin_id = pins[0].id

    registry.unpin(pin_id)
    assert registry.list_pins("run-1") == []
    db.close()


def test_unpin_nonexistent_is_noop(tmp_path: Path) -> None:
    """Unpin on non-existent pin_id is a no-op."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)
    registry.unpin(99999)  # Should not raise
    db.close()


def test_duplicate_pin_content_creates_two(tmp_path: Path) -> None:
    """Pinning same content twice creates two entries (not duplicate-suppressed)."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)

    registry.pin(run_id="run-1", content="Same content", reason="r1")
    registry.pin(run_id="run-1", content="Same content", reason="r2")
    pins = registry.list_pins("run-1")
    assert len(pins) == 2
    db.close()


def test_as_content_blocks(tmp_path: Path) -> None:
    """as_content_blocks() returns ContentBlock objects for compaction."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)

    registry.pin(run_id="run-1", content="Invariant A", reason="safety")
    registry.pin(run_id="run-1", content="Invariant B", reason="safety")

    blocks = registry.as_content_blocks("run-1")
    assert len(blocks) == 2
    assert all(isinstance(b, ContentBlock) for b in blocks)
    assert all(b.block_type == BlockType.pinned for b in blocks)
    db.close()


def test_pinned_blocks_feed_into_compaction(tmp_path: Path) -> None:
    """Pinned blocks from registry feed into CompactionEngine.compact()."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)

    registry.pin(run_id="run-1", content="Must survive compaction", reason="safety")

    pinned_blocks = registry.as_content_blocks("run-1")
    other_blocks = [
        ContentBlock(content=f"recent-{i}", block_type=BlockType.recent, token_count=50)
        for i in range(10)
    ]
    all_blocks = pinned_blocks + other_blocks

    engine = CompactionEngine(recent_turns_keep=2)
    result = engine.compact(all_blocks, budget=200)

    # Pinned block from registry must survive
    pinned_in_result = [b for b in result if b.block_type == BlockType.pinned]
    assert len(pinned_in_result) == 1
    assert pinned_in_result[0].content == "Must survive compaction"
    db.close()


# ── Import smoke tests ──


def test_import_context_pin_registry_from_agents() -> None:
    from openeinstein.agents import ContextPinRegistry as _CPR  # noqa: F401


def test_import_context_pin_record_from_persistence() -> None:
    from openeinstein.persistence import ContextPinRecord as _CPR  # noqa: F401
