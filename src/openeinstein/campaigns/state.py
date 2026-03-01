"""Campaign state machine with checkpoint/resume and idempotency enforcement."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field

from openeinstein.gateway import ControlPlane
from openeinstein.persistence import CampaignDB

CampaignRunState = Literal[
    "initialized",
    "running",
    "generating",
    "gating",
    "completed",
    "failed",
    "stopped",
]


class CampaignSnapshot(BaseModel):
    run_id: str
    state: CampaignRunState
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: str


class CandidateRecordResult(BaseModel):
    candidate_id: int
    idempotency_key: str
    created: bool


_ALLOWED_TRANSITIONS: dict[CampaignRunState, set[CampaignRunState]] = {
    "initialized": {"running", "stopped", "failed"},
    "running": {"generating", "gating", "completed", "stopped", "failed"},
    "generating": {"gating", "running", "stopped", "failed"},
    "gating": {"running", "completed", "stopped", "failed"},
    "stopped": {"running", "failed"},
    "completed": set(),
    "failed": set(),
}


class CampaignStateMachine:
    """State manager for campaign execution lifecycle."""

    def __init__(self, db: CampaignDB, control_plane: ControlPlane) -> None:
        self._db = db
        self._control = control_plane

    def initialize_run(self, run_id: str | None = None, metadata: dict[str, Any] | None = None) -> str:
        started_run_id = self._control.start_run(run_id=run_id)
        payload = dict(metadata or {})
        payload.setdefault("idempotency_keys", [])
        self._db.upsert_campaign_state(started_run_id, "initialized", payload)
        self._control.emit_event(started_run_id, "campaign_initialized", {"state": "initialized"})
        return started_run_id

    def snapshot(self, run_id: str) -> CampaignSnapshot:
        row = self._db.get_campaign_state(run_id)
        if row is None:
            raise KeyError(f"Unknown campaign run: {run_id}")
        return CampaignSnapshot(
            run_id=run_id,
            state=row["state"],
            metadata=row["metadata"],
            updated_at=row["updated_at"],
        )

    def transition(
        self,
        run_id: str,
        to_state: CampaignRunState,
        metadata_update: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> CampaignSnapshot:
        current = self.snapshot(run_id)
        allowed = _ALLOWED_TRANSITIONS[current.state]
        if to_state not in allowed:
            raise ValueError(f"Invalid transition: {current.state} -> {to_state}")

        merged = dict(current.metadata)
        if metadata_update:
            merged.update(metadata_update)
        self._db.upsert_campaign_state(run_id, to_state, merged)

        if to_state == "stopped":
            self._control.stop_run(run_id, reason=reason)
        elif to_state == "running":
            self._control.resume_run(run_id)
        elif to_state in {"completed", "failed"}:
            self._control.emit_event(run_id, f"campaign_{to_state}", {"reason": reason or ""})
        else:
            self._control.emit_event(
                run_id, "campaign_state_changed", {"from": current.state, "to": to_state}
            )

        return self.snapshot(run_id)

    def checkpoint(self, run_id: str, payload: dict[str, Any]) -> CampaignSnapshot:
        current = self.snapshot(run_id)
        metadata = dict(current.metadata)
        metadata["checkpoint"] = payload
        self._db.upsert_campaign_state(run_id, current.state, metadata)
        self._control.emit_event(run_id, "campaign_checkpoint", {"keys": sorted(payload.keys())})
        return self.snapshot(run_id)

    def resume(self, run_id: str) -> CampaignSnapshot:
        snapshot = self.snapshot(run_id)
        self._control.emit_event(run_id, "campaign_resume_requested", {"state": snapshot.state})
        return snapshot

    @staticmethod
    def generate_idempotency_key(run_id: str, candidate_key: str, gate_name: str) -> str:
        raw = f"{run_id}::{candidate_key}::{gate_name}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def record_candidate(
        self,
        run_id: str,
        *,
        candidate_key: str,
        candidate_data: dict[str, Any],
        gate_name: str = "candidate",
    ) -> CandidateRecordResult:
        current = self.snapshot(run_id)
        metadata = dict(current.metadata)
        idempotency_keys = set(metadata.get("idempotency_keys", []))
        idempotency_key = self.generate_idempotency_key(run_id, candidate_key, gate_name)
        if idempotency_key in idempotency_keys:
            for candidate in self._db.get_candidates(run_id):
                if candidate.candidate_key == candidate_key:
                    return CandidateRecordResult(
                        candidate_id=candidate.id,
                        idempotency_key=idempotency_key,
                        created=False,
                    )
            # Metadata can drift from table state after external edits; treat as recoverable and reinsert.

        candidate_id = self._db.add_candidate(run_id, candidate_key, candidate_data)
        idempotency_keys.add(idempotency_key)
        metadata["idempotency_keys"] = sorted(idempotency_keys)
        self._db.upsert_campaign_state(run_id, current.state, metadata)
        self._control.emit_event(
            run_id,
            "campaign_candidate_recorded",
            {"candidate_key": candidate_key, "candidate_id": candidate_id},
        )
        return CandidateRecordResult(
            candidate_id=candidate_id,
            idempotency_key=idempotency_key,
            created=True,
        )
