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


@dataclass(frozen=True)
class RuntimeRunRecord:
    run_id: str
    campaign_path: str
    status: str
    desired_state: str
    replay_cursor: int
    current_step_index: int
    max_steps: int
    max_runtime_minutes: int
    max_cost_usd: float
    max_tokens: int
    parameters: dict[str, Any]
    error: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class RuntimeStepRecord:
    id: int
    run_id: str
    step_id: str
    step_index: int
    phase: str
    status: str
    attempt: int
    input_payload: dict[str, Any]
    output_payload: dict[str, Any] | None
    error: str | None
    started_at: str
    ended_at: str | None


@dataclass(frozen=True)
class RuntimeEventRecord:
    run_id: str
    seq: int
    event_type: str
    step_id: str | None
    payload: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class RuntimeUsageRecord:
    id: int
    run_id: str
    role: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    created_at: str


@dataclass(frozen=True)
class ContextPinRecord:
    id: int
    run_id: str
    block_type: str
    content: str
    reason: str
    created_at: str


@dataclass(frozen=True)
class DurableNoteRecord:
    id: int
    run_id: str
    step_id: str
    content: str
    created_at: str


class CampaignDB:
    """Typed CRUD wrapper around the OpenEinstein SQLite schema."""

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
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

        CREATE TABLE IF NOT EXISTS runtime_runs (
            run_id TEXT PRIMARY KEY,
            campaign_path TEXT NOT NULL,
            status TEXT NOT NULL,
            desired_state TEXT NOT NULL,
            replay_cursor INTEGER NOT NULL DEFAULT 0,
            current_step_index INTEGER NOT NULL DEFAULT 0,
            max_steps INTEGER NOT NULL,
            max_runtime_minutes INTEGER NOT NULL,
            max_cost_usd REAL NOT NULL,
            max_tokens INTEGER NOT NULL,
            parameters_json TEXT NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runtime_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            step_index INTEGER NOT NULL,
            phase TEXT NOT NULL,
            status TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 1,
            input_json TEXT NOT NULL,
            output_json TEXT,
            error TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            UNIQUE(run_id, step_id)
        );

        CREATE TABLE IF NOT EXISTS runtime_events (
            run_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            step_id TEXT,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (run_id, seq)
        );

        CREATE TABLE IF NOT EXISTS runtime_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            role TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            cost_usd REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """
        self._conn.executescript(schema_sql)
        self._conn.commit()
        self.apply_migration("0001_initial", "-- initial schema")
        self.apply_migration("0002_runtime_executor", "-- runtime executor tables")
        self.apply_migration(
            "0003_context_pins",
            """
            CREATE TABLE IF NOT EXISTS context_pins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                block_type TEXT NOT NULL,
                content TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """,
        )
        self.apply_migration(
            "0004_durable_notes",
            """
            CREATE TABLE IF NOT EXISTS durable_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """,
        )

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

    def create_runtime_run(
        self,
        *,
        run_id: str,
        campaign_path: str,
        status: str,
        desired_state: str,
        max_steps: int,
        max_runtime_minutes: int,
        max_cost_usd: float,
        max_tokens: int,
        parameters: dict[str, Any] | None = None,
    ) -> RuntimeRunRecord:
        now = self._now()
        self._conn.execute(
            """
            INSERT INTO runtime_runs (
                run_id, campaign_path, status, desired_state, replay_cursor, current_step_index,
                max_steps, max_runtime_minutes, max_cost_usd, max_tokens, parameters_json,
                error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                run_id,
                campaign_path,
                status,
                desired_state,
                max_steps,
                max_runtime_minutes,
                max_cost_usd,
                max_tokens,
                json.dumps(parameters or {}),
                now,
                now,
            ),
        )
        self._conn.commit()
        record = self.get_runtime_run(run_id)
        if record is None:
            raise RuntimeError("runtime run creation failed")
        return record

    def get_runtime_run(self, run_id: str) -> RuntimeRunRecord | None:
        row = self._conn.execute(
            """
            SELECT run_id, campaign_path, status, desired_state, replay_cursor, current_step_index,
                   max_steps, max_runtime_minutes, max_cost_usd, max_tokens, parameters_json,
                   error, created_at, updated_at
            FROM runtime_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return RuntimeRunRecord(
            run_id=row["run_id"],
            campaign_path=row["campaign_path"],
            status=row["status"],
            desired_state=row["desired_state"],
            replay_cursor=int(row["replay_cursor"]),
            current_step_index=int(row["current_step_index"]),
            max_steps=int(row["max_steps"]),
            max_runtime_minutes=int(row["max_runtime_minutes"]),
            max_cost_usd=float(row["max_cost_usd"]),
            max_tokens=int(row["max_tokens"]),
            parameters=json.loads(row["parameters_json"]),
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_runtime_runs(self) -> list[RuntimeRunRecord]:
        rows = self._conn.execute(
            """
            SELECT run_id, campaign_path, status, desired_state, replay_cursor, current_step_index,
                   max_steps, max_runtime_minutes, max_cost_usd, max_tokens, parameters_json,
                   error, created_at, updated_at
            FROM runtime_runs
            ORDER BY updated_at, run_id
            """
        ).fetchall()
        return [
            RuntimeRunRecord(
                run_id=row["run_id"],
                campaign_path=row["campaign_path"],
                status=row["status"],
                desired_state=row["desired_state"],
                replay_cursor=int(row["replay_cursor"]),
                current_step_index=int(row["current_step_index"]),
                max_steps=int(row["max_steps"]),
                max_runtime_minutes=int(row["max_runtime_minutes"]),
                max_cost_usd=float(row["max_cost_usd"]),
                max_tokens=int(row["max_tokens"]),
                parameters=json.loads(row["parameters_json"]),
                error=row["error"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def update_runtime_run_state(
        self,
        run_id: str,
        *,
        status: str | None = None,
        desired_state: str | None = None,
        replay_cursor: int | None = None,
        current_step_index: int | None = None,
        error: str | None = None,
    ) -> None:
        current = self.get_runtime_run(run_id)
        if current is None:
            raise KeyError(f"Unknown runtime run: {run_id}")
        self._conn.execute(
            """
            UPDATE runtime_runs
            SET status = ?,
                desired_state = ?,
                replay_cursor = ?,
                current_step_index = ?,
                error = ?,
                updated_at = ?
            WHERE run_id = ?
            """,
            (
                status or current.status,
                desired_state or current.desired_state,
                replay_cursor if replay_cursor is not None else current.replay_cursor,
                current_step_index
                if current_step_index is not None
                else current.current_step_index,
                error,
                self._now(),
                run_id,
            ),
        )
        self._conn.commit()

    def append_runtime_event(
        self,
        run_id: str,
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
        step_id: str | None = None,
    ) -> RuntimeEventRecord:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS seq FROM runtime_events WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        next_seq = int(row["seq"] if row is not None else 0) + 1
        now = self._now()
        self._conn.execute(
            """
            INSERT INTO runtime_events (run_id, seq, event_type, step_id, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, next_seq, event_type, step_id, json.dumps(payload or {}), now),
        )
        self._conn.execute(
            """
            UPDATE runtime_runs
            SET replay_cursor = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (next_seq, now, run_id),
        )
        self._conn.commit()
        return RuntimeEventRecord(
            run_id=run_id,
            seq=next_seq,
            event_type=event_type,
            step_id=step_id,
            payload=payload or {},
            created_at=now,
        )

    def get_runtime_events(
        self,
        run_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[RuntimeEventRecord]:
        rows = self._conn.execute(
            """
            SELECT run_id, seq, event_type, step_id, payload_json, created_at
            FROM runtime_events
            WHERE run_id = ? AND seq > ?
            ORDER BY seq
            LIMIT ?
            """,
            (run_id, after_seq, limit),
        ).fetchall()
        return [
            RuntimeEventRecord(
                run_id=row["run_id"],
                seq=int(row["seq"]),
                event_type=row["event_type"],
                step_id=row["step_id"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def start_runtime_step(
        self,
        *,
        run_id: str,
        step_id: str,
        step_index: int,
        phase: str,
        attempt: int,
        input_payload: dict[str, Any] | None = None,
    ) -> RuntimeStepRecord:
        now = self._now()
        self._conn.execute(
            """
            INSERT INTO runtime_steps (
                run_id, step_id, step_index, phase, status, attempt, input_json, output_json,
                error, started_at, ended_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, NULL)
            ON CONFLICT(run_id, step_id) DO UPDATE SET
                step_index = excluded.step_index,
                phase = excluded.phase,
                status = excluded.status,
                attempt = excluded.attempt,
                input_json = excluded.input_json,
                started_at = excluded.started_at,
                ended_at = NULL,
                error = NULL
            """,
            (
                run_id,
                step_id,
                step_index,
                phase,
                "running",
                attempt,
                json.dumps(input_payload or {}),
                now,
            ),
        )
        self._conn.execute(
            """
            UPDATE runtime_runs
            SET current_step_index = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (step_index, now, run_id),
        )
        self._conn.commit()
        step = self.get_runtime_step(run_id, step_id)
        if step is None:
            raise RuntimeError("runtime step creation failed")
        return step

    def finish_runtime_step(
        self,
        *,
        run_id: str,
        step_id: str,
        status: str,
        output_payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> RuntimeStepRecord:
        self._conn.execute(
            """
            UPDATE runtime_steps
            SET status = ?, output_json = ?, error = ?, ended_at = ?
            WHERE run_id = ? AND step_id = ?
            """,
            (status, json.dumps(output_payload or {}), error, self._now(), run_id, step_id),
        )
        self._conn.execute(
            "UPDATE runtime_runs SET updated_at = ? WHERE run_id = ?",
            (self._now(), run_id),
        )
        self._conn.commit()
        step = self.get_runtime_step(run_id, step_id)
        if step is None:
            raise RuntimeError("runtime step completion failed")
        return step

    def get_runtime_step(self, run_id: str, step_id: str) -> RuntimeStepRecord | None:
        row = self._conn.execute(
            """
            SELECT id, run_id, step_id, step_index, phase, status, attempt, input_json, output_json,
                   error, started_at, ended_at
            FROM runtime_steps
            WHERE run_id = ? AND step_id = ?
            """,
            (run_id, step_id),
        ).fetchone()
        if row is None:
            return None
        return RuntimeStepRecord(
            id=int(row["id"]),
            run_id=row["run_id"],
            step_id=row["step_id"],
            step_index=int(row["step_index"]),
            phase=row["phase"],
            status=row["status"],
            attempt=int(row["attempt"]),
            input_payload=json.loads(row["input_json"]),
            output_payload=(
                json.loads(row["output_json"]) if row["output_json"] is not None else None
            ),
            error=row["error"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
        )

    def list_runtime_steps(self, run_id: str) -> list[RuntimeStepRecord]:
        rows = self._conn.execute(
            """
            SELECT id, run_id, step_id, step_index, phase, status, attempt, input_json, output_json,
                   error, started_at, ended_at
            FROM runtime_steps
            WHERE run_id = ?
            ORDER BY step_index, id
            """,
            (run_id,),
        ).fetchall()
        return [
            RuntimeStepRecord(
                id=int(row["id"]),
                run_id=row["run_id"],
                step_id=row["step_id"],
                step_index=int(row["step_index"]),
                phase=row["phase"],
                status=row["status"],
                attempt=int(row["attempt"]),
                input_payload=json.loads(row["input_json"]),
                output_payload=(
                    json.loads(row["output_json"]) if row["output_json"] is not None else None
                ),
                error=row["error"],
                started_at=row["started_at"],
                ended_at=row["ended_at"],
            )
            for row in rows
        ]

    def add_runtime_usage(
        self,
        *,
        run_id: str,
        role: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO runtime_usage (
                run_id, role, provider, model, prompt_tokens, completion_tokens, cost_usd, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                role,
                provider,
                model,
                int(prompt_tokens),
                int(completion_tokens),
                float(cost_usd),
                self._now(),
            ),
        )
        self._conn.commit()
        return self._required_lastrowid(cursor)

    def get_runtime_usage(self, run_id: str) -> list[RuntimeUsageRecord]:
        rows = self._conn.execute(
            """
            SELECT id, run_id, role, provider, model, prompt_tokens, completion_tokens, cost_usd, created_at
            FROM runtime_usage
            WHERE run_id = ?
            ORDER BY id
            """,
            (run_id,),
        ).fetchall()
        return [
            RuntimeUsageRecord(
                id=int(row["id"]),
                run_id=row["run_id"],
                role=row["role"],
                provider=row["provider"],
                model=row["model"],
                prompt_tokens=int(row["prompt_tokens"]),
                completion_tokens=int(row["completion_tokens"]),
                cost_usd=float(row["cost_usd"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_runtime_cost_totals(self, run_id: str) -> dict[str, float]:
        row = self._conn.execute(
            """
            SELECT COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                   COALESCE(SUM(cost_usd), 0.0) AS cost_usd
            FROM runtime_usage
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return {"prompt_tokens": 0.0, "completion_tokens": 0.0, "cost_usd": 0.0}
        return {
            "prompt_tokens": float(row["prompt_tokens"]),
            "completion_tokens": float(row["completion_tokens"]),
            "cost_usd": float(row["cost_usd"]),
        }

    # ── Context Pins CRUD ──

    def add_context_pin(
        self,
        run_id: str,
        block_type: str,
        content: str,
        reason: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO context_pins (run_id, block_type, content, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, block_type, content, reason, self._now()),
        )
        self._conn.commit()
        return self._required_lastrowid(cur)

    def get_context_pins(self, run_id: str) -> list[ContextPinRecord]:
        rows = self._conn.execute(
            "SELECT id, run_id, block_type, content, reason, created_at FROM context_pins WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [
            ContextPinRecord(
                id=row["id"],
                run_id=row["run_id"],
                block_type=row["block_type"],
                content=row["content"],
                reason=row["reason"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def remove_context_pin(self, pin_id: int) -> None:
        self._conn.execute("DELETE FROM context_pins WHERE id = ?", (pin_id,))
        self._conn.commit()

    # ── Durable Notes CRUD ──

    def add_durable_note(self, run_id: str, step_id: str, content: str) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO durable_notes (run_id, step_id, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, step_id, content, self._now()),
        )
        self._conn.commit()
        return self._required_lastrowid(cur)

    def get_durable_notes(self, run_id: str) -> list[DurableNoteRecord]:
        rows = self._conn.execute(
            "SELECT id, run_id, step_id, content, created_at FROM durable_notes WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [
            DurableNoteRecord(
                id=row["id"],
                run_id=row["run_id"],
                step_id=row["step_id"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def journal_mode(self) -> str:
        row = self._conn.execute("PRAGMA journal_mode;").fetchone()
        value = row[0] if row is not None else ""
        return str(value)
