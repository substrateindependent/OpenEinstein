"""Control plane primitives for run lifecycle and event streaming."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from shutil import copy2
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

RunStatus = Literal["running", "stopped", "completed", "failed"]


class RunEvent(BaseModel):
    """Serializable event emitted for a run."""

    run_id: str
    event_type: str
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ArtifactRecord(BaseModel):
    """Run-scoped artifact metadata."""

    run_id: str
    name: str
    path: str
    attached_at: str


class RunRecord(BaseModel):
    """Stored status for a run."""

    run_id: str
    status: RunStatus
    started_at: str
    updated_at: str
    artifacts: list[ArtifactRecord] = Field(default_factory=list)


class ControlPlane(Protocol):
    """Protocol boundary for lifecycle operations."""

    def issue_run_id(self) -> str: ...

    def start_run(self, run_id: str | None = None) -> str: ...

    def emit_event(
        self, run_id: str, event_type: str, payload: dict[str, Any] | None = None
    ) -> RunEvent: ...

    def get_events(self, run_id: str) -> list[RunEvent]: ...

    def get_status(self, run_id: str) -> RunStatus: ...

    def stop_run(self, run_id: str, reason: str | None = None) -> None: ...

    def resume_run(self, run_id: str) -> None: ...

    def wait_for_status(
        self,
        run_id: str,
        target_statuses: set[RunStatus],
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.1,
    ) -> RunStatus: ...

    def attach_artifact(self, run_id: str, name: str, source_path: str | Path) -> ArtifactRecord: ...

    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]: ...


class FileBackedControlPlane:
    """Run lifecycle manager with JSONL event streams and file-backed state."""

    def __init__(self, root: str | Path = Path(".openeinstein") / "control-plane") -> None:
        self._root = Path(root)
        self._runs_dir = self._root / "runs"
        self._events_dir = self._root / "events"
        self._artifacts_dir = self._root / "artifacts"
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._events_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._events_cache: dict[str, list[RunEvent]] = {}

    @staticmethod
    def _now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _run_state_path(self, run_id: str) -> Path:
        return self._runs_dir / f"{run_id}.json"

    def _event_stream_path(self, run_id: str) -> Path:
        return self._events_dir / f"{run_id}.jsonl"

    def _load_run_record(self, run_id: str) -> RunRecord:
        path = self._run_state_path(run_id)
        if not path.exists():
            raise KeyError(f"Unknown run_id: {run_id}")
        return RunRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def _save_run_record(self, record: RunRecord) -> None:
        self._run_state_path(record.run_id).write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )

    def issue_run_id(self) -> str:
        return f"run-{uuid.uuid4().hex[:12]}"

    def latest_run_id(self) -> str | None:
        records: list[RunRecord] = []
        for path in self._runs_dir.glob("*.json"):
            records.append(RunRecord.model_validate_json(path.read_text(encoding="utf-8")))
        if not records:
            return None
        records.sort(key=lambda record: record.updated_at)
        return records[-1].run_id

    def start_run(self, run_id: str | None = None) -> str:
        created_run_id = run_id or self.issue_run_id()
        now = self._now_iso()
        record = RunRecord(
            run_id=created_run_id,
            status="running",
            started_at=now,
            updated_at=now,
            artifacts=[],
        )
        self._save_run_record(record)
        self.emit_event(created_run_id, "run_started", {})
        return created_run_id

    def emit_event(
        self, run_id: str, event_type: str, payload: dict[str, Any] | None = None
    ) -> RunEvent:
        self._load_run_record(run_id)
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            timestamp=self._now_iso(),
            payload=payload or {},
        )
        with self._event_stream_path(run_id).open("a", encoding="utf-8") as stream:
            stream.write(event.model_dump_json())
            stream.write("\n")
        self._events_cache.setdefault(run_id, []).append(event)
        return event

    def get_events(self, run_id: str) -> list[RunEvent]:
        if run_id in self._events_cache:
            return list(self._events_cache[run_id])
        path = self._event_stream_path(run_id)
        if not path.exists():
            return []
        events = [
            RunEvent.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self._events_cache[run_id] = events
        return list(events)

    def _set_status(self, run_id: str, status: RunStatus) -> None:
        record = self._load_run_record(run_id)
        updated = record.model_copy(update={"status": status, "updated_at": self._now_iso()})
        self._save_run_record(updated)

    def get_status(self, run_id: str) -> RunStatus:
        return self._load_run_record(run_id).status

    def stop_run(self, run_id: str, reason: str | None = None) -> None:
        self._set_status(run_id, "stopped")
        payload = {"reason": reason} if reason else {}
        self.emit_event(run_id, "run_stopped", payload)

    def resume_run(self, run_id: str) -> None:
        self._set_status(run_id, "running")
        self.emit_event(run_id, "run_resumed", {})

    def wait_for_status(
        self,
        run_id: str,
        target_statuses: set[RunStatus],
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.1,
    ) -> RunStatus:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() <= deadline:
            status = self.get_status(run_id)
            if status in target_statuses:
                return status
            time.sleep(poll_interval_seconds)
        raise TimeoutError(
            f"Timed out waiting for run {run_id} to reach {sorted(target_statuses)}"
        )

    def attach_artifact(self, run_id: str, name: str, source_path: str | Path) -> ArtifactRecord:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(source)
        run_dir = self._artifacts_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        target = run_dir / source.name
        copy2(source, target)
        artifact = ArtifactRecord(
            run_id=run_id,
            name=name,
            path=str(target),
            attached_at=self._now_iso(),
        )
        record = self._load_run_record(run_id)
        updated = record.model_copy(
            update={"artifacts": [*record.artifacts, artifact], "updated_at": self._now_iso()}
        )
        self._save_run_record(updated)
        self.emit_event(run_id, "artifact_attached", {"name": name, "path": str(target)})
        return artifact

    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]:
        return list(self._load_run_record(run_id).artifacts)
