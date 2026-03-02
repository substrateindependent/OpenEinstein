"""Event sequencing and sync support for dashboard websocket streams."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class EventEnvelope(BaseModel):
    v: int = 1
    seq: int
    ts: str
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class EventHub:
    """In-memory event stream with monotonically increasing sequence ids."""

    def __init__(self, max_events: int = 10_000) -> None:
        self._seq = 0
        self._events: deque[EventEnvelope] = deque(maxlen=max_events)

    def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> EventEnvelope:
        self._seq += 1
        event = EventEnvelope(seq=self._seq, ts=_utc_now_iso(), type=event_type, payload=payload or {})
        self._events.append(event)
        return event

    def sync_after(self, last_seq: int) -> list[EventEnvelope]:
        return [event for event in self._events if event.seq > last_seq]

    def heartbeat(self) -> EventEnvelope:
        return self.publish("heartbeat", {"intervalSeconds": 15})
