"""Campaign state machine with checkpoint/resume and idempotency enforcement."""

from __future__ import annotations

import hashlib
import threading
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

    def __init__(
        self,
        db: CampaignDB,
        control_plane: ControlPlane,
        concurrent_tracker: ConcurrentStepTracker | None = None,
    ) -> None:
        self._db = db
        self._control = control_plane
        self.concurrent_tracker = concurrent_tracker

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


# ── Default allowed concurrent phase pairs ──

_DEFAULT_ALLOWED_CONCURRENT: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"literature", "planning"}),
        frozenset({"literature", "generating"}),
        frozenset({"literature", "gating"}),
        frozenset({"literature", "verifying"}),
        frozenset({"generating", "gating"}),
    }
)


class ConcurrentStepTracker:
    """Tracks active steps per lane and enforces phase concurrency rules.

    Rules:
    - Two steps with the **same** phase are never allowed concurrently.
    - Two steps with **different** phases are allowed only when their pair
      appears in *allowed_concurrent_transitions*.
    """

    allowed_concurrent_transitions: frozenset[frozenset[str]]

    def __init__(
        self,
        allowed_concurrent: frozenset[frozenset[str]] | None = None,
    ) -> None:
        self.allowed_concurrent_transitions = (
            allowed_concurrent if allowed_concurrent is not None else _DEFAULT_ALLOWED_CONCURRENT
        )
        self._active: dict[str, set[str]] = {}  # lane_name → set of step_ids
        self._phase_map: dict[str, str] = {}  # step_id → phase
        self._lock = threading.Lock()

    # ── Public API ──

    def register_step(self, lane_name: str, step_id: str, phase: str) -> None:
        """Register a step as active. Raises ValueError on rule violation."""
        with self._lock:
            self._check_concurrent_rules(phase)
            self._active.setdefault(lane_name, set()).add(step_id)
            self._phase_map[step_id] = phase

    def complete_step(self, lane_name: str, step_id: str) -> None:
        """Remove a completed step from tracking. No-op if not found."""
        with self._lock:
            lane_steps = self._active.get(lane_name)
            if lane_steps is not None:
                lane_steps.discard(step_id)
                if not lane_steps:
                    del self._active[lane_name]
            self._phase_map.pop(step_id, None)

    @property
    def lane_status(self) -> dict[str, dict[str, Any]]:
        """Per-lane active step counts and step IDs."""
        with self._lock:
            result: dict[str, dict[str, Any]] = {}
            for lane_name, step_ids in self._active.items():
                result[lane_name] = {
                    "active": len(step_ids),
                    "step_ids": set(step_ids),
                }
            return result

    def can_run_phase(self, phase: str) -> bool:
        """Check whether *phase* can be registered without violating rules."""
        with self._lock:
            try:
                self._check_concurrent_rules(phase)
                return True
            except ValueError:
                return False

    # ── Internal ──

    def _check_concurrent_rules(self, new_phase: str) -> None:
        """Raise ValueError if *new_phase* conflicts with active phases."""
        active_phases = set(self._phase_map.values())
        if not active_phases:
            return

        # Same-phase duplication is always rejected
        if new_phase in active_phases:
            raise ValueError(
                f"Phase '{new_phase}' is already active; "
                f"concurrent duplicate phases are not allowed"
            )

        # Check every active phase against the new phase
        for existing in active_phases:
            pair = frozenset({existing, new_phase})
            if pair not in self.allowed_concurrent_transitions:
                raise ValueError(
                    f"Phases '{existing}' and '{new_phase}' cannot run concurrent; "
                    f"pair not in allowed_concurrent_transitions"
                )
