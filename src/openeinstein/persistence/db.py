"""SQLite persistence layer for campaign/runtime state."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CandidateRecord:
    id: int
    run_id: str
    candidate_key: str
    data: dict[str, Any]
    gate_result: dict[str, Any] | None


@dataclass(frozen=True)
class FailureRecord:
    id: int
    run_id: str
    candidate_key: str
    failure_type: str
    details: dict[str, Any]


@dataclass(frozen=True)
class TraceSpanRecord:
    id: int
    run_id: str
    span_name: str
    attributes: dict[str, Any]
    started_at: str
    ended_at: str | None


@dataclass(frozen=True)
class EvalResultRecord:
    id: int
    run_id: str
    suite_name: str
    case_name: str
    passed: bool
    expected: dict[str, Any]
    actual: dict[str, Any]
    created_at: str


class CampaignDB:
    """Typed CRUD wrapper around the OpenEinstein SQLite schema."""

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._create_schema()

    def close(self) -> None:
        self._conn.close()

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _create_schema(self) -> None:
        schema_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS campaign_state (
            run_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            candidate_key TEXT NOT NULL,
            data_json TEXT NOT NULL,
            gate_result_json TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS failure_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            candidate_key TEXT NOT NULL,
            failure_type TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trace_spans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            span_name TEXT NOT NULL,
            attributes_json TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT
        );

        CREATE TABLE IF NOT EXISTS eval_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            suite_name TEXT NOT NULL,
            case_name TEXT NOT NULL,
            passed INTEGER NOT NULL,
            expected_json TEXT NOT NULL,
            actual_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS approval_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            action TEXT NOT NULL,
            approved INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        );
        """
        self._conn.executescript(schema_sql)
        self._conn.commit()
        self.apply_migration("0001_initial", "-- initial schema")

    def _required_lastrowid(self, cursor: sqlite3.Cursor) -> int:
        lastrowid = cursor.lastrowid
        if lastrowid is None:
            raise RuntimeError("expected sqlite rowid, got None")
        return int(lastrowid)

    def apply_migration(self, version: str, sql: str) -> None:
        row = self._conn.execute(
            "SELECT version FROM schema_migrations WHERE version = ?", (version,)
        ).fetchone()
        if row is not None:
            return
        if sql.strip() and not sql.strip().startswith("--"):
            self._conn.executescript(sql)
        self._conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, self._now()),
        )
        self._conn.commit()

    def upsert_campaign_state(self, run_id: str, state: str, metadata: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO campaign_state (run_id, state, metadata_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                state = excluded.state,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (run_id, state, json.dumps(metadata), self._now()),
        )
        self._conn.commit()

    def get_campaign_state(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT run_id, state, metadata_json, updated_at FROM campaign_state WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "state": row["state"],
            "metadata": json.loads(row["metadata_json"]),
            "updated_at": row["updated_at"],
        }

    def add_candidate(self, run_id: str, candidate_key: str, data: dict[str, Any]) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO candidates (run_id, candidate_key, data_json, gate_result_json, created_at)
            VALUES (?, ?, ?, NULL, ?)
            """,
            (run_id, candidate_key, json.dumps(data), self._now()),
        )
        self._conn.commit()
        return self._required_lastrowid(cursor)

    def update_gate_result(self, candidate_id: int, gate_result: dict[str, Any]) -> None:
        self._conn.execute(
            "UPDATE candidates SET gate_result_json = ? WHERE id = ?",
            (json.dumps(gate_result), candidate_id),
        )
        self._conn.commit()

    def get_candidates(self, run_id: str) -> list[CandidateRecord]:
        rows = self._conn.execute(
            "SELECT id, run_id, candidate_key, data_json, gate_result_json FROM candidates WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [
            CandidateRecord(
                id=int(row["id"]),
                run_id=row["run_id"],
                candidate_key=row["candidate_key"],
                data=json.loads(row["data_json"]),
                gate_result=(
                    None
                    if row["gate_result_json"] is None
                    else json.loads(row["gate_result_json"])
                ),
            )
            for row in rows
        ]

    def log_failure(
        self,
        run_id: str,
        candidate_key: str,
        failure_type: str,
        details: dict[str, Any],
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO failure_log (run_id, candidate_key, failure_type, details_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, candidate_key, failure_type, json.dumps(details), self._now()),
        )
        self._conn.commit()
        return self._required_lastrowid(cursor)

    def get_failure_log(self, run_id: str) -> list[FailureRecord]:
        rows = self._conn.execute(
            "SELECT id, run_id, candidate_key, failure_type, details_json FROM failure_log WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [
            FailureRecord(
                id=int(row["id"]),
                run_id=row["run_id"],
                candidate_key=row["candidate_key"],
                failure_type=row["failure_type"],
                details=json.loads(row["details_json"]),
            )
            for row in rows
        ]

    def add_trace_span(
        self,
        run_id: str,
        span_name: str,
        attributes: dict[str, Any],
        started_at: str,
        ended_at: str | None,
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO trace_spans (run_id, span_name, attributes_json, started_at, ended_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, span_name, json.dumps(attributes), started_at, ended_at),
        )
        self._conn.commit()
        return self._required_lastrowid(cursor)

    def add_eval_result(
        self,
        run_id: str,
        suite_name: str,
        case_name: str,
        passed: bool,
        expected: dict[str, Any],
        actual: dict[str, Any],
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO eval_results (run_id, suite_name, case_name, passed, expected_json, actual_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                suite_name,
                case_name,
                int(passed),
                json.dumps(expected),
                json.dumps(actual),
                self._now(),
            ),
        )
        self._conn.commit()
        return self._required_lastrowid(cursor)

    def get_eval_results(self, run_id: str | None = None) -> list[EvalResultRecord]:
        if run_id is None:
            rows = self._conn.execute(
                """
                SELECT id, run_id, suite_name, case_name, passed, expected_json, actual_json, created_at
                FROM eval_results
                ORDER BY id
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, run_id, suite_name, case_name, passed, expected_json, actual_json, created_at
                FROM eval_results
                WHERE run_id = ?
                ORDER BY id
                """,
                (run_id,),
            ).fetchall()
        return [
            EvalResultRecord(
                id=int(row["id"]),
                run_id=row["run_id"],
                suite_name=row["suite_name"],
                case_name=row["case_name"],
                passed=bool(row["passed"]),
                expected=json.loads(row["expected_json"]),
                actual=json.loads(row["actual_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def log_approval(self, run_id: str, action: str, approved: bool, reason: str | None) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO approval_log (run_id, action, approved, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, action, int(approved), reason, self._now()),
        )
        self._conn.commit()
        return self._required_lastrowid(cursor)

    def get_statistics(self, run_id: str) -> dict[str, int]:
        candidates = self._conn.execute(
            "SELECT COUNT(*) AS count FROM candidates WHERE run_id = ?", (run_id,)
        ).fetchone()
        failures = self._conn.execute(
            "SELECT COUNT(*) AS count FROM failure_log WHERE run_id = ?", (run_id,)
        ).fetchone()
        spans = self._conn.execute(
            "SELECT COUNT(*) AS count FROM trace_spans WHERE run_id = ?", (run_id,)
        ).fetchone()
        evals = self._conn.execute(
            "SELECT COUNT(*) AS count FROM eval_results WHERE run_id = ?", (run_id,)
        ).fetchone()
        approvals = self._conn.execute(
            "SELECT COUNT(*) AS count FROM approval_log WHERE run_id = ?", (run_id,)
        ).fetchone()

        return {
            "candidates": int(candidates["count"] if candidates else 0),
            "failures": int(failures["count"] if failures else 0),
            "trace_spans": int(spans["count"] if spans else 0),
            "eval_results": int(evals["count"] if evals else 0),
            "approval_log": int(approvals["count"] if approvals else 0),
        }

    def get_trace_spans(self, run_id: str) -> list[TraceSpanRecord]:
        rows = self._conn.execute(
            """
            SELECT id, run_id, span_name, attributes_json, started_at, ended_at
            FROM trace_spans
            WHERE run_id = ?
            ORDER BY id
            """,
            (run_id,),
        ).fetchall()
        return [
            TraceSpanRecord(
                id=int(row["id"]),
                run_id=row["run_id"],
                span_name=row["span_name"],
                attributes=json.loads(row["attributes_json"]),
                started_at=row["started_at"],
                ended_at=row["ended_at"],
            )
            for row in rows
        ]

    def journal_mode(self) -> str:
        row = self._conn.execute("PRAGMA journal_mode;").fetchone()
        value = row[0] if row is not None else ""
        return str(value)
