"""Typed websocket protocol payloads for dashboard control stream."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ClientMessageType = Literal[
    "connect",
    "sync_request",
    "approval_decision",
    "set_verbosity",
    "run_command",
]

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class WSClientMessage(BaseModel):
    type: ClientMessageType
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    client_id: str | None = None
    client_version: str | None = None

    @field_validator("idempotency_key")
    @classmethod
    def _validate_idempotency_key(cls, v: str | None) -> str | None:
        if v is not None and not _UUID_RE.match(v):
            raise ValueError(f"idempotency_key must be a valid UUID, got: {v!r}")
        return v
