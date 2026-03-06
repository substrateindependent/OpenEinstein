"""Integration tests for webhook bridge hook and CLI commands (Story 5.3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from openeinstein.cli.main import app
from openeinstein.gateway.hooks import HookContext, HookRegistry
from openeinstein.gateway.webhooks import WebhookDispatcher


class TestWebhookBridgeHook:
    def test_bridge_hook_dispatches_matching_event(self) -> None:
        """Bridge hook forwards matching events to the webhook dispatcher."""
        from openeinstein.gateway.hooks import WebhookBridgeHook

        dispatcher = WebhookDispatcher()
        mock_send = MagicMock(return_value=True)
        dispatcher.register("https://example.com/hook", ["candidate_generated"], "secret")

        bridge = WebhookBridgeHook(dispatcher)
        ctx = HookContext(
            hook_point="candidate_generated",  # type: ignore[arg-type]
            run_id="run-test",
            payload={"candidate_key": "cand-001"},
        )

        with patch("openeinstein.gateway.webhooks._send_webhook_request", mock_send):
            result = bridge(ctx)

        assert result is None or result.allow is True
        # Webhook should have been dispatched (blocking mode for testing)
        mock_send.assert_called_once()

    def test_bridge_hook_skips_non_matching_event(self) -> None:
        """Bridge hook does not dispatch when no webhooks match the event."""
        from openeinstein.gateway.hooks import WebhookBridgeHook

        dispatcher = WebhookDispatcher()
        mock_send = MagicMock(return_value=True)
        dispatcher.register("https://example.com/hook", ["gate_passed"], "secret")

        bridge = WebhookBridgeHook(dispatcher)
        ctx = HookContext(
            hook_point="candidate_generated",  # type: ignore[arg-type]
            run_id="run-test",
            payload={},
        )

        with patch("openeinstein.gateway.webhooks._send_webhook_request", mock_send):
            result = bridge(ctx)

        assert result is None or result.allow is True
        mock_send.assert_not_called()

    def test_bridge_hook_registered_in_hook_registry(self) -> None:
        """Bridge hook can be registered and fires via HookRegistry dispatch."""
        from openeinstein.gateway.hooks import WebhookBridgeHook

        registry = HookRegistry()
        dispatcher = WebhookDispatcher()
        mock_send = MagicMock(return_value=True)
        dispatcher.register("https://example.com/hook", ["gate_passed"], "secret")

        bridge = WebhookBridgeHook(dispatcher)
        registry.register("gate_passed", bridge)  # type: ignore[arg-type]

        ctx = HookContext(
            hook_point="gate_passed",  # type: ignore[arg-type]
            run_id="run-test",
            payload={"backend": "sympy"},
        )

        with patch("openeinstein.gateway.webhooks._send_webhook_request", mock_send):
            result = registry.dispatch("gate_passed", ctx)  # type: ignore[arg-type]

        assert result.allow is True
        mock_send.assert_called_once()

    def test_bridge_hook_error_does_not_block(self) -> None:
        """Bridge hook errors are caught and don't block the hook chain."""
        from openeinstein.gateway.hooks import WebhookBridgeHook

        dispatcher = MagicMock(spec=WebhookDispatcher)
        dispatcher.dispatch.side_effect = RuntimeError("dispatch error")

        bridge = WebhookBridgeHook(dispatcher)
        ctx = HookContext(
            hook_point="candidate_generated",  # type: ignore[arg-type]
            payload={},
        )
        # Should not raise
        result = bridge(ctx)
        assert result is None or result.allow is True


class TestWebhookCLICommands:
    def test_webhook_list_empty(self, tmp_path: Path) -> None:
        config_file = tmp_path / "webhooks.yaml"
        config_file.write_text("webhooks: []\n")
        runner = CliRunner()
        result = runner.invoke(app, ["webhook", "list", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "No webhooks" in result.output or "0" in result.output

    def test_webhook_list_shows_entries(self, tmp_path: Path) -> None:
        config_file = tmp_path / "webhooks.yaml"
        config_file.write_text(
            "webhooks:\n"
            "  - url: https://a.com/hook\n"
            "    events: [gate_passed]\n"
            "    secret: s1\n"
            "  - url: https://b.com/hook\n"
            "    events: [candidate_generated]\n"
            "    secret: s2\n"
        )
        runner = CliRunner()
        result = runner.invoke(app, ["webhook", "list", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "a.com" in result.output
        assert "b.com" in result.output

    @patch("openeinstein.gateway.webhooks._send_webhook_request")
    def test_webhook_test_command(self, mock_send: MagicMock, tmp_path: Path) -> None:
        mock_send.return_value = True
        config_file = tmp_path / "webhooks.yaml"
        config_file.write_text(
            "webhooks:\n"
            "  - url: https://test.com/hook\n"
            "    events: [test]\n"
            "    secret: my_secret\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            app, ["webhook", "test", "--config", str(config_file), "--url", "https://test.com/hook"]
        )
        assert result.exit_code == 0

    def test_webhook_test_invalid_url(self, tmp_path: Path) -> None:
        config_file = tmp_path / "webhooks.yaml"
        config_file.write_text("webhooks: []\n")
        runner = CliRunner()
        result = runner.invoke(
            app, ["webhook", "test", "--config", str(config_file), "--url", "https://not-registered.com/hook"]
        )
        assert result.exit_code == 0
        assert "not found" in result.output.lower() or "not registered" in result.output.lower()
