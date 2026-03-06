"""Outbound webhook dispatcher with HMAC signing, retry, and event filtering."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

_logger = logging.getLogger(__name__)


class WebhookRegistration(BaseModel):
    """A single webhook subscription."""

    url: str
    events: list[str]
    secret: str


class WebhookConfig(BaseModel):
    """Top-level webhook configuration."""

    webhooks: list[WebhookRegistration] = Field(default_factory=list)


def load_webhook_config(path: str | Path) -> WebhookConfig:
    """Load webhook configuration from YAML. Returns empty config if file missing."""
    config_path = Path(path)
    if not config_path.exists():
        return WebhookConfig()
    content = config_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        return WebhookConfig()
    raw_hooks = data.get("webhooks", [])
    if not isinstance(raw_hooks, list):
        return WebhookConfig()
    registrations = []
    for entry in raw_hooks:
        if isinstance(entry, dict):
            registrations.append(
                WebhookRegistration(
                    url=entry.get("url", ""),
                    events=entry.get("events", []),
                    secret=entry.get("secret", ""),
                )
            )
    return WebhookConfig(webhooks=registrations)


def _send_webhook_request(url: str, body: str, signature: str) -> bool:
    """Send a single HTTP POST webhook request. Returns True on success."""
    try:
        req = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-OpenEinstein-Signature": signature,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        _logger.debug("Webhook request failed for %s", url, exc_info=True)
        return False


class WebhookDispatcher:
    """Dispatches webhook events to registered HTTP endpoints with HMAC signing."""

    def __init__(self, *, max_retries: int = 3, backoff_base: float = 0.1) -> None:
        self._webhooks: list[WebhookRegistration] = []
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._lock = threading.Lock()

    def register(self, url: str, events: list[str], secret: str) -> None:
        """Register a webhook endpoint for the given event types."""
        if not secret:
            raise ValueError("Webhook secret must not be empty")
        with self._lock:
            self._webhooks.append(
                WebhookRegistration(url=url, events=events, secret=secret)
            )

    def unregister(self, url: str) -> None:
        """Remove a webhook by URL. No-op if not found."""
        with self._lock:
            self._webhooks = [w for w in self._webhooks if w.url != url]

    def list_webhooks(self) -> list[WebhookRegistration]:
        """Return a copy of registered webhooks."""
        with self._lock:
            return list(self._webhooks)

    def dispatch(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        blocking: bool = False,
    ) -> None:
        """Dispatch an event to all subscribed webhooks.

        Args:
            event_type: The event type string.
            payload: JSON-serializable payload.
            blocking: If True, dispatch synchronously. If False, dispatch in a thread.
        """
        with self._lock:
            targets = [w for w in self._webhooks if event_type in w.events]

        if not targets:
            return

        body = json.dumps({"event_type": event_type, "payload": payload}, default=str)

        if blocking:
            for webhook in targets:
                self._deliver(webhook, body)
        else:
            for webhook in targets:
                thread = threading.Thread(
                    target=self._deliver,
                    args=(webhook, body),
                    daemon=True,
                )
                thread.start()

    def _deliver(self, webhook: WebhookRegistration, body: str) -> None:
        """Deliver a webhook with retries and exponential backoff."""
        signature = hmac.new(
            webhook.secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        for attempt in range(self._max_retries):
            if _send_webhook_request(webhook.url, body, signature):
                return
            if attempt < self._max_retries - 1:
                delay = self._backoff_base * (2 ** attempt)
                time.sleep(delay)

        _logger.warning(
            "Webhook delivery failed after %d attempts: %s",
            self._max_retries,
            webhook.url,
        )

    @classmethod
    def from_config(cls, config: WebhookConfig) -> WebhookDispatcher:
        """Create a dispatcher pre-loaded with webhooks from config."""
        dispatcher = cls()
        for reg in config.webhooks:
            dispatcher.register(reg.url, reg.events, reg.secret)
        return dispatcher
