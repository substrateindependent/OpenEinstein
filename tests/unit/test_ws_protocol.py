"""Unit tests for WS protocol idempotency key and client identity extensions (Story 7.1)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from openeinstein.gateway.ws.protocol import WSClientMessage


class TestIdempotencyKeyField:
    def test_idempotency_key_none_by_default(self) -> None:
        msg = WSClientMessage(type="run_command", payload={"command": "start"})
        assert msg.idempotency_key is None

    def test_idempotency_key_accepts_valid_uuid(self) -> None:
        key = str(uuid.uuid4())
        msg = WSClientMessage(type="run_command", payload={}, idempotency_key=key)
        assert msg.idempotency_key == key

    def test_idempotency_key_rejects_non_uuid(self) -> None:
        with pytest.raises(ValidationError, match="idempotency_key"):
            WSClientMessage(type="run_command", payload={}, idempotency_key="not-a-uuid")

    def test_idempotency_key_on_approval_decision(self) -> None:
        key = str(uuid.uuid4())
        msg = WSClientMessage(type="approval_decision", payload={}, idempotency_key=key)
        assert msg.idempotency_key == key

    def test_idempotency_key_on_connect_type(self) -> None:
        """Connect messages can also carry idempotency_key (though unusual)."""
        key = str(uuid.uuid4())
        msg = WSClientMessage(type="connect", payload={}, idempotency_key=key)
        assert msg.idempotency_key == key

    def test_missing_key_backward_compatible(self) -> None:
        """Old clients without idempotency_key still parse successfully."""
        raw = {"type": "run_command", "payload": {"command": "start"}}
        msg = WSClientMessage.model_validate(raw)
        assert msg.idempotency_key is None


class TestClientIdentityFields:
    def test_client_id_none_by_default(self) -> None:
        msg = WSClientMessage(type="connect", payload={})
        assert msg.client_id is None

    def test_client_version_none_by_default(self) -> None:
        msg = WSClientMessage(type="connect", payload={})
        assert msg.client_version is None

    def test_client_id_accepts_string(self) -> None:
        msg = WSClientMessage(type="connect", payload={}, client_id="dashboard-v2")
        assert msg.client_id == "dashboard-v2"

    def test_client_version_accepts_string(self) -> None:
        msg = WSClientMessage(type="connect", payload={}, client_version="1.2.3")
        assert msg.client_version == "1.2.3"

    def test_both_identity_fields_together(self) -> None:
        msg = WSClientMessage(
            type="connect",
            payload={},
            client_id="cli-agent",
            client_version="0.7.0",
        )
        assert msg.client_id == "cli-agent"
        assert msg.client_version == "0.7.0"

    def test_old_client_without_identity_still_parses(self) -> None:
        raw = {"type": "connect", "payload": {"token": "abc"}}
        msg = WSClientMessage.model_validate(raw)
        assert msg.client_id is None
        assert msg.client_version is None


class TestHandlerExtractsIdempotencyKey:
    def test_message_with_key_round_trips(self) -> None:
        """Verify idempotency_key survives serialization/deserialization."""
        key = str(uuid.uuid4())
        msg = WSClientMessage(type="run_command", payload={"command": "start"}, idempotency_key=key)
        raw = msg.model_dump()
        restored = WSClientMessage.model_validate(raw)
        assert restored.idempotency_key == key

    def test_client_identity_round_trips(self) -> None:
        msg = WSClientMessage(
            type="connect",
            payload={},
            client_id="test-client",
            client_version="2.0.0",
        )
        raw = msg.model_dump()
        restored = WSClientMessage.model_validate(raw)
        assert restored.client_id == "test-client"
        assert restored.client_version == "2.0.0"


class TestHandlerStoresClientIdentity:
    def test_connect_frame_client_id_in_session(self) -> None:
        """Handler should extract client_id from connect frame for session state.

        This tests the data model; actual handler session storage is in Story 7.2.
        """
        raw = {
            "type": "connect",
            "payload": {"token": "test-token"},
            "client_id": "dashboard-v2",
            "client_version": "1.0.0",
        }
        msg = WSClientMessage.model_validate(raw)
        # Simulating what the handler would do:
        session_state: dict[str, str | None] = {
            "client_id": msg.client_id,
            "client_version": msg.client_version,
        }
        assert session_state["client_id"] == "dashboard-v2"
        assert session_state["client_version"] == "1.0.0"


class TestImports:
    def test_ws_protocol_importable(self) -> None:
        from openeinstein.gateway.ws.protocol import WSClientMessage as WSM

        assert WSM is not None
