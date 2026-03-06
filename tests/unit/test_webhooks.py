"""Unit tests for outbound webhook dispatcher (Story 5.2)."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openeinstein.gateway.webhooks import (
    WebhookDispatcher,
    WebhookRegistration,
    load_webhook_config,
)


class TestWebhookRegistration:
    def test_register_webhook(self) -> None:
        dispatcher = WebhookDispatcher()
        dispatcher.register("https://example.com/hook", ["candidate_generated"], "secret123")
        assert len(dispatcher.list_webhooks()) == 1

    def test_register_multiple_webhooks(self) -> None:
        dispatcher = WebhookDispatcher()
        dispatcher.register("https://a.com/hook", ["gate_passed"], "s1")
        dispatcher.register("https://b.com/hook", ["gate_failed"], "s2")
        assert len(dispatcher.list_webhooks()) == 2

    def test_unregister_webhook(self) -> None:
        dispatcher = WebhookDispatcher()
        dispatcher.register("https://example.com/hook", ["candidate_generated"], "secret123")
        dispatcher.unregister("https://example.com/hook")
        assert len(dispatcher.list_webhooks()) == 0

    def test_unregister_nonexistent_is_noop(self) -> None:
        dispatcher = WebhookDispatcher()
        dispatcher.unregister("https://nonexistent.com/hook")
        assert len(dispatcher.list_webhooks()) == 0

    def test_empty_secret_raises(self) -> None:
        dispatcher = WebhookDispatcher()
        with pytest.raises(ValueError, match="secret"):
            dispatcher.register("https://example.com/hook", ["gate_passed"], "")


class TestWebhookDispatch:
    @patch("openeinstein.gateway.webhooks._send_webhook_request")
    def test_dispatch_sends_to_subscribed_webhook(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        dispatcher = WebhookDispatcher()
        dispatcher.register("https://a.com/hook", ["candidate_generated"], "secret")
        dispatcher.dispatch("candidate_generated", {"key": "value"}, blocking=True)
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "https://a.com/hook"

    @patch("openeinstein.gateway.webhooks._send_webhook_request")
    def test_dispatch_filters_by_event_type(self, mock_send: MagicMock) -> None:
        """Webhook subscribed to candidate_generated should NOT fire for gate_passed."""
        mock_send.return_value = True
        dispatcher = WebhookDispatcher()
        dispatcher.register("https://a.com/hook", ["candidate_generated"], "secret")
        dispatcher.dispatch("gate_passed", {"key": "value"}, blocking=True)
        mock_send.assert_not_called()

    @patch("openeinstein.gateway.webhooks._send_webhook_request")
    def test_dispatch_to_multiple_matching_webhooks(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        dispatcher = WebhookDispatcher()
        dispatcher.register("https://a.com/hook", ["gate_passed"], "s1")
        dispatcher.register("https://b.com/hook", ["gate_passed", "gate_failed"], "s2")
        dispatcher.dispatch("gate_passed", {}, blocking=True)
        assert mock_send.call_count == 2

    @patch("openeinstein.gateway.webhooks._send_webhook_request")
    def test_dispatch_with_no_webhooks_is_noop(self, mock_send: MagicMock) -> None:
        dispatcher = WebhookDispatcher()
        dispatcher.dispatch("candidate_generated", {"data": "test"}, blocking=True)
        mock_send.assert_not_called()

    @patch("openeinstein.gateway.webhooks._send_webhook_request")
    def test_hmac_signature_is_correct(self, mock_send: MagicMock) -> None:
        """Verify the HMAC-SHA256 signature passed to the send function."""
        mock_send.return_value = True
        secret = "my_webhook_secret"
        dispatcher = WebhookDispatcher()
        dispatcher.register("https://a.com/hook", ["test_event"], secret)
        payload = {"key": "value"}
        dispatcher.dispatch("test_event", payload, blocking=True)

        call_args = mock_send.call_args
        sent_body = call_args[0][1]
        sent_signature = call_args[0][2]

        expected_sig = hmac.new(
            secret.encode("utf-8"),
            sent_body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        assert sent_signature == expected_sig

    @patch("openeinstein.gateway.webhooks._send_webhook_request")
    def test_dispatch_unreachable_url_retries(self, mock_send: MagicMock) -> None:
        """Unreachable webhook should retry up to max_retries times."""
        mock_send.side_effect = [False, False, True]
        dispatcher = WebhookDispatcher(max_retries=3)
        dispatcher.register("https://unreachable.com/hook", ["test_event"], "secret")
        dispatcher.dispatch("test_event", {}, blocking=True)
        assert mock_send.call_count == 3

    @patch("openeinstein.gateway.webhooks._send_webhook_request")
    def test_dispatch_all_retries_fail_logs(self, mock_send: MagicMock) -> None:
        """All retries failing should not raise, just log."""
        mock_send.return_value = False
        dispatcher = WebhookDispatcher(max_retries=2)
        dispatcher.register("https://unreachable.com/hook", ["test_event"], "secret")
        # Should not raise
        dispatcher.dispatch("test_event", {}, blocking=True)
        assert mock_send.call_count == 2


class TestWebhookConfig:
    def test_load_webhook_config(self, tmp_path: Path) -> None:
        config_yaml = tmp_path / "webhooks.yaml"
        config_yaml.write_text(
            "webhooks:\n"
            "  - url: https://example.com/hook\n"
            "    events: [candidate_generated, gate_passed]\n"
            "    secret: my_secret\n"
        )
        config = load_webhook_config(config_yaml)
        assert len(config.webhooks) == 1
        assert config.webhooks[0].url == "https://example.com/hook"
        assert "candidate_generated" in config.webhooks[0].events

    def test_load_webhook_config_missing_file_returns_empty(self, tmp_path: Path) -> None:
        config = load_webhook_config(tmp_path / "nonexistent.yaml")
        assert len(config.webhooks) == 0

    def test_load_webhook_config_empty_file(self, tmp_path: Path) -> None:
        config_yaml = tmp_path / "webhooks.yaml"
        config_yaml.write_text("")
        config = load_webhook_config(config_yaml)
        assert len(config.webhooks) == 0

    def test_webhook_config_model(self) -> None:
        reg = WebhookRegistration(
            url="https://example.com/hook",
            events=["gate_passed"],
            secret="secret123",
        )
        assert reg.url == "https://example.com/hook"
        assert reg.secret == "secret123"

    def test_dispatcher_from_config(self, tmp_path: Path) -> None:
        config_yaml = tmp_path / "webhooks.yaml"
        config_yaml.write_text(
            "webhooks:\n"
            "  - url: https://a.com/hook\n"
            "    events: [gate_passed]\n"
            "    secret: s1\n"
            "  - url: https://b.com/hook\n"
            "    events: [gate_failed]\n"
            "    secret: s2\n"
        )
        config = load_webhook_config(config_yaml)
        dispatcher = WebhookDispatcher.from_config(config)
        assert len(dispatcher.list_webhooks()) == 2
