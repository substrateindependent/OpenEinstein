"""Typed websocket protocol payloads for dashboard control stream."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ClientMessageType = Literal[
    "connect",
    "sync_request",
    "approval_decision",
    "set_verbosity",
    "run_command",
]


class WSClientMessage(BaseModel):
    type: ClientMessageType
    payload: dict[str, Any] = Field(default_factory=dict)
