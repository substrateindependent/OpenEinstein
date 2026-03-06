"""Idempotency cache for WS protocol deduplication."""

from __future__ import annotations

import threading
import time
from typing import Any

from pydantic import BaseModel, Field


class CachedResult(BaseModel):
    """A cached response for a previously-processed idempotency key."""

    key: str
    result: dict[str, Any]
    created_at: float = Field(default_factory=time.monotonic)


class IdempotencyCache:
    """Thread-safe in-memory idempotency cache with TTL-based expiry.

    Parameters
    ----------
    ttl_seconds:
        How long entries remain valid.  Default 300 s (5 minutes).
    cleanup_interval:
        Run automatic expired-entry cleanup every *N* ``check_and_store``
        calls.  Set to 0 to disable automatic cleanup.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float = 300.0,
        cleanup_interval: int = 100,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._cleanup_interval = cleanup_interval
        self._cache: dict[str, CachedResult] = {}
        self._lock = threading.Lock()
        self._ops_since_cleanup = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_store(
        self,
        key: str,
        result: dict[str, Any],
    ) -> CachedResult | None:
        """Check whether *key* was already processed.

        * If *key* is new (or expired), store *result* and return ``None``
          (the caller should proceed with normal processing).
        * If *key* already exists and is not expired, return the
          ``CachedResult`` (the caller should return the cached response
          instead of re-processing).
        """
        with self._lock:
            self._maybe_cleanup()
            existing = self._cache.get(key)
            if existing is not None:
                if not self._is_expired(existing):
                    return existing
                # Expired — treat as new
                del self._cache[key]
            self._cache[key] = CachedResult(key=key, result=result)
            return None

    def cleanup_expired(self) -> int:
        """Remove all expired entries.  Returns count of removed entries."""
        with self._lock:
            return self._do_cleanup()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _is_expired(self, entry: CachedResult) -> bool:
        return (time.monotonic() - entry.created_at) > self._ttl_seconds

    def _maybe_cleanup(self) -> None:
        self._ops_since_cleanup += 1
        if self._cleanup_interval > 0 and self._ops_since_cleanup >= self._cleanup_interval:
            self._do_cleanup()

    def _do_cleanup(self) -> int:
        expired_keys = [k for k, v in self._cache.items() if self._is_expired(v)]
        for k in expired_keys:
            del self._cache[k]
        self._ops_since_cleanup = 0
        return len(expired_keys)
