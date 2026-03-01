"""Unit tests for persistence layer CRUD and durability."""

from __future__ import annotations

from pathlib import Path

from openeinstein.persistence import CampaignDB


def test_persistence_crud_operations(tmp_path: Path) -> None:
    db = CampaignDB(tmp_path / "campaign.db")

    db.upsert_campaign_state("run-1", "INITIALIZED", {"x": 1})
    state = db.get_campaign_state("run-1")
    assert state is not None
    assert state["state"] == "INITIALIZED"

    candidate_id = db.add_candidate("run-1", "cand-1", {"alpha": 1})
    db.update_gate_result(candidate_id, {"passed": True})
    candidates = db.get_candidates("run-1")
    assert len(candidates) == 1
    assert candidates[0].gate_result == {"passed": True}

    db.log_failure("run-1", "cand-1", "timeout", {"seconds": 10})
    failures = db.get_failure_log("run-1")
    assert len(failures) == 1

    db.add_trace_span("run-1", "gate", {"k": "v"}, "t0", "t1")
    db.add_eval_result("run-1", "suite", "case", True, {"a": 1}, {"a": 1})
    db.log_approval("run-1", "shell_exec", True, "approved")

    stats = db.get_statistics("run-1")
    assert stats["candidates"] == 1
    assert stats["failures"] == 1
    assert stats["trace_spans"] == 1
    assert stats["eval_results"] == 1
    assert stats["approval_log"] == 1

    assert db.journal_mode().lower() == "wal"
    db.close()


def test_persistence_survives_close_and_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "campaign.db"

    db = CampaignDB(db_path)
    db.upsert_campaign_state("run-2", "EVALUATING", {"step": 2})
    db.add_candidate("run-2", "cand-2", {"beta": 2})
    db.close()

    reopened = CampaignDB(db_path)
    state = reopened.get_campaign_state("run-2")
    candidates = reopened.get_candidates("run-2")

    assert state is not None
    assert state["state"] == "EVALUATING"
    assert len(candidates) == 1
    reopened.close()


def test_migration_idempotency(tmp_path: Path) -> None:
    db = CampaignDB(tmp_path / "campaign.db")
    db.apply_migration("9999_test", "-- noop")
    db.apply_migration("9999_test", "-- noop")

    rows = db._conn.execute(
        "SELECT COUNT(*) AS count FROM schema_migrations WHERE version = ?", ("9999_test",)
    ).fetchone()
    assert rows is not None
    assert int(rows["count"]) == 1
    db.close()
