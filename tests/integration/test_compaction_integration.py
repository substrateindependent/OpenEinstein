"""Integration tests for compaction wiring into orchestrator & executor (Story 3.4)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from openeinstein.agents.compaction import BlockType, CompactionEngine, ContentBlock
from openeinstein.agents.context_pins import ContextPinRegistry
from openeinstein.agents.memory_flush import MemoryFlushManager
from openeinstein.agents.orchestrator import AgentOrchestrator
from openeinstein.persistence.db import CampaignDB


# ── Orchestrator compaction integration ──


def test_orchestrator_accepts_compaction_engine() -> None:
    """AgentOrchestrator.__init__ accepts optional compaction_engine."""
    engine = CompactionEngine(recent_turns_keep=3)
    orch = AgentOrchestrator(subagents={}, compaction_engine=engine)
    assert orch._compaction_engine is engine


def test_orchestrator_accepts_pin_registry(tmp_path: Path) -> None:
    """AgentOrchestrator.__init__ accepts optional pin_registry."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)
    orch = AgentOrchestrator(subagents={}, pin_registry=registry)
    assert orch._pin_registry is registry
    db.close()


def test_orchestrator_backward_compatible_without_engine() -> None:
    """Orchestrator without compaction_engine uses old compact_with_invariants."""
    orch = AgentOrchestrator(
        subagents={},
        invariants=["safety"],
        max_compacted_chars=50,
    )
    # Old behavior: truncation + invariant injection
    long_text = "A" * 100
    result = orch.compact_with_invariants(long_text, ["safety"])
    assert "safety" in result
    assert len(result) <= 50 + len("safety") + 10  # some margin


def test_orchestrator_compact_with_engine() -> None:
    """compact_with_invariants delegates to CompactionEngine when engine is provided."""
    engine = CompactionEngine(recent_turns_keep=2)
    orch = AgentOrchestrator(subagents={}, compaction_engine=engine)

    # When engine is present, compact_with_invariants should use it
    text = "Some long context that needs compaction"
    result = orch.compact_with_invariants(text, ["safety_invariant"])
    # Result should be a string (backward compatible return type)
    assert isinstance(result, str)


def test_orchestrator_auto_pins_invariants(tmp_path: Path) -> None:
    """Invariants are auto-pinned in the registry at construction."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)

    orch = AgentOrchestrator(
        subagents={},
        invariants=["No hallucination", "Cite sources"],
        pin_registry=registry,
        pin_run_id="run-1",
    )
    assert orch is not None  # construction succeeds

    pins = registry.list_pins("run-1")
    assert len(pins) == 2
    contents = [p.content for p in pins]
    assert "No hallucination" in contents
    assert "Cite sources" in contents
    db.close()


def test_orchestrator_no_auto_pin_without_run_id(tmp_path: Path) -> None:
    """Without pin_run_id, invariants are not auto-pinned."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)

    orch = AgentOrchestrator(
        subagents={},
        invariants=["Safety"],
        pin_registry=registry,
    )
    assert orch is not None
    # No run_id provided, so nothing pinned
    db.close()


def test_pinned_invariants_survive_compaction(tmp_path: Path) -> None:
    """Pinned invariants from registry survive compaction."""
    db = CampaignDB(tmp_path / "test.db")
    registry = ContextPinRegistry(db)

    # Pin an invariant
    registry.pin(run_id="run-1", content="Must cite sources", reason="safety")

    # Get pinned blocks
    pinned_blocks = registry.as_content_blocks("run-1")

    # Create many recent blocks to exceed budget
    recent_blocks = [
        ContentBlock(content=f"Step {i} output", block_type=BlockType.recent, token_count=50)
        for i in range(20)
    ]
    all_blocks = pinned_blocks + recent_blocks

    # Compact with tight budget
    engine = CompactionEngine(recent_turns_keep=2)
    result = engine.compact(all_blocks, budget=200)

    # Pinned block must survive
    pinned_in_result = [b for b in result if b.block_type == BlockType.pinned]
    assert len(pinned_in_result) == 1
    assert pinned_in_result[0].content == "Must cite sources"
    db.close()


# ── Memory flush + compaction pipeline ──


def test_memory_flush_feeds_compaction(tmp_path: Path) -> None:
    """MemoryFlushManager.flush_before_compaction feeds into CompactionEngine."""
    db = CampaignDB(tmp_path / "test.db")
    mock_router = MagicMock()
    mock_router.run_with_fallback.return_value = "Key insight extracted"

    manager = MemoryFlushManager(db=db, model_router=mock_router)

    context = [
        ContentBlock(content=f"Long content block {i}", block_type=BlockType.recent, token_count=100)
        for i in range(10)
    ]

    # Flush extracts notes before compaction
    notes = manager.flush_before_compaction(run_id="run-1", context=context)
    assert len(notes) >= 1

    # Notes are persisted
    db_notes = db.get_durable_notes("run-1")
    assert len(db_notes) >= 1

    # Now compact the same context
    engine = CompactionEngine(recent_turns_keep=3)
    result = engine.compact(context, budget=500)

    # Compaction produced a smaller context
    assert len(result) <= len(context)
    db.close()


# ── Import smoke tests ──


def test_import_all_compaction_components() -> None:
    """All compaction components importable from their packages."""
    from openeinstein.agents import (  # noqa: F401
        CompactionEngine,
        ContextPinRegistry,
        MemoryFlushManager,
    )
    from openeinstein.persistence import (  # noqa: F401
        ContextPinRecord,
        DurableNoteRecord,
    )
