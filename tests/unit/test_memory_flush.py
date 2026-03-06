"""Unit tests for Memory Flush Manager (Story 3.3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from openeinstein.agents.compaction import BlockType, ContentBlock
from openeinstein.agents.memory_flush import DurableNote, MemoryFlushManager
from openeinstein.persistence.db import CampaignDB


# ── DurableNote model ──


def test_durable_note_fields() -> None:
    """DurableNote has required fields."""
    note = DurableNote(run_id="run-1", step_id="step-1", content="Important finding")
    assert note.run_id == "run-1"
    assert note.step_id == "step-1"
    assert note.content == "Important finding"


# ── CampaignDB durable_notes CRUD ──


def test_db_add_and_get_durable_notes(tmp_path: Path) -> None:
    """add_durable_note inserts and get_durable_notes retrieves."""
    db = CampaignDB(tmp_path / "test.db")
    note_id = db.add_durable_note(
        run_id="run-1", step_id="step-1", content="Key insight"
    )
    assert note_id > 0

    notes = db.get_durable_notes("run-1")
    assert len(notes) == 1
    assert notes[0].content == "Key insight"
    assert notes[0].step_id == "step-1"
    db.close()


def test_db_get_durable_notes_empty(tmp_path: Path) -> None:
    """get_durable_notes with no notes returns empty list."""
    db = CampaignDB(tmp_path / "test.db")
    notes = db.get_durable_notes("nonexistent")
    assert notes == []
    db.close()


def test_db_multiple_durable_notes(tmp_path: Path) -> None:
    """Multiple notes for the same run_id all persist."""
    db = CampaignDB(tmp_path / "test.db")
    db.add_durable_note(run_id="run-1", step_id="step-1", content="Note A")
    db.add_durable_note(run_id="run-1", step_id="step-2", content="Note B")
    db.add_durable_note(run_id="run-2", step_id="step-1", content="Note C")

    notes_1 = db.get_durable_notes("run-1")
    notes_2 = db.get_durable_notes("run-2")
    assert len(notes_1) == 2
    assert len(notes_2) == 1
    db.close()


def test_db_durable_notes_survive_reconnect(tmp_path: Path) -> None:
    """Notes persist after closing and reopening DB."""
    db_path = tmp_path / "test.db"
    db = CampaignDB(db_path)
    db.add_durable_note(run_id="run-1", step_id="step-1", content="Durable note")
    db.close()

    db2 = CampaignDB(db_path)
    notes = db2.get_durable_notes("run-1")
    assert len(notes) == 1
    assert notes[0].content == "Durable note"
    db2.close()


# ── MemoryFlushManager ──


def test_flush_with_mock_router(tmp_path: Path) -> None:
    """flush_before_compaction calls model router and persists notes."""
    db = CampaignDB(tmp_path / "test.db")

    mock_router = MagicMock()
    # Model call returns extracted notes as a string
    mock_router.run_with_fallback.return_value = "Key insight: gravity waves detected"

    manager = MemoryFlushManager(db=db, model_router=mock_router)

    context = [
        ContentBlock(content="Step 1 result", block_type=BlockType.recent, token_count=10),
        ContentBlock(content="Step 2 result", block_type=BlockType.recent, token_count=10),
    ]
    notes = manager.flush_before_compaction(run_id="run-1", context=context)

    assert len(notes) >= 1
    assert any("gravity waves" in n.content for n in notes)

    # Verify model router was called
    mock_router.run_with_fallback.assert_called_once()
    call_args = mock_router.run_with_fallback.call_args
    assert call_args[0][0] == "fast"  # role

    # Verify notes persisted to DB
    db_notes = db.get_durable_notes("run-1")
    assert len(db_notes) >= 1
    db.close()


def test_flush_with_empty_context(tmp_path: Path) -> None:
    """flush_before_compaction with empty context returns empty notes."""
    db = CampaignDB(tmp_path / "test.db")
    mock_router = MagicMock()

    manager = MemoryFlushManager(db=db, model_router=mock_router)
    notes = manager.flush_before_compaction(run_id="run-1", context=[])

    assert notes == []
    # Should not call model on empty context
    mock_router.run_with_fallback.assert_not_called()
    db.close()


def test_flush_model_failure_returns_empty_notes(tmp_path: Path) -> None:
    """Model call failure during flush logs error but returns empty notes."""
    db = CampaignDB(tmp_path / "test.db")
    mock_router = MagicMock()
    mock_router.run_with_fallback.side_effect = RuntimeError("Model unavailable")

    manager = MemoryFlushManager(db=db, model_router=mock_router)

    context = [
        ContentBlock(content="Some content", block_type=BlockType.recent, token_count=10),
    ]
    notes = manager.flush_before_compaction(run_id="run-1", context=context)

    # Should return empty notes, not raise
    assert notes == []
    db.close()


def test_flush_does_not_block_on_failure(tmp_path: Path) -> None:
    """Flush failure does not raise, allowing compaction to proceed."""
    db = CampaignDB(tmp_path / "test.db")
    mock_router = MagicMock()
    mock_router.run_with_fallback.side_effect = Exception("Unexpected error")

    manager = MemoryFlushManager(db=db, model_router=mock_router)

    context = [
        ContentBlock(content="Content", block_type=BlockType.recent, token_count=5),
    ]
    # Should not raise
    notes = manager.flush_before_compaction(run_id="run-1", context=context)
    assert notes == []
    db.close()


# ── Import smoke tests ──


def test_import_memory_flush_manager_from_agents() -> None:
    from openeinstein.agents import MemoryFlushManager as _MFM  # noqa: F401


def test_import_durable_note_record_from_persistence() -> None:
    from openeinstein.persistence import DurableNoteRecord as _DNR  # noqa: F401
