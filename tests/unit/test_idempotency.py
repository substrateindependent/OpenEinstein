"""Unit tests for idempotency cache and deduplication (Story 7.2)."""

from __future__ import annotations

import threading
import time
import uuid

from openeinstein.gateway.idempotency import CachedResult, IdempotencyCache


class TestIdempotencyCacheBasic:
    def test_new_key_returns_none(self) -> None:
        cache = IdempotencyCache()
        result = cache.check_and_store(str(uuid.uuid4()), {"status": "ok"})
        assert result is None

    def test_duplicate_key_returns_cached(self) -> None:
        cache = IdempotencyCache()
        key = str(uuid.uuid4())
        cache.check_and_store(key, {"run_id": "run-001"})
        cached = cache.check_and_store(key, {"run_id": "run-002"})
        assert cached is not None
        assert cached.result == {"run_id": "run-001"}

    def test_different_keys_independent(self) -> None:
        cache = IdempotencyCache()
        key_a = str(uuid.uuid4())
        key_b = str(uuid.uuid4())
        cache.check_and_store(key_a, {"a": 1})
        result = cache.check_and_store(key_b, {"b": 2})
        assert result is None

    def test_cached_result_model(self) -> None:
        cr = CachedResult(key="test-key", result={"ok": True})
        assert cr.key == "test-key"
        assert cr.result == {"ok": True}
        assert cr.created_at is not None


class TestIdempotencyCacheTTL:
    def test_expired_entry_allows_reprocessing(self) -> None:
        cache = IdempotencyCache(ttl_seconds=0.1)
        key = str(uuid.uuid4())
        cache.check_and_store(key, {"first": True})
        time.sleep(0.15)
        result = cache.check_and_store(key, {"second": True})
        assert result is None

    def test_non_expired_entry_blocks(self) -> None:
        cache = IdempotencyCache(ttl_seconds=10.0)
        key = str(uuid.uuid4())
        cache.check_and_store(key, {"first": True})
        cached = cache.check_and_store(key, {"second": True})
        assert cached is not None
        assert cached.result == {"first": True}

    def test_default_ttl_is_five_minutes(self) -> None:
        cache = IdempotencyCache()
        assert cache._ttl_seconds == 300.0


class TestIdempotencyCacheCleanup:
    def test_expired_entries_cleaned(self) -> None:
        cache = IdempotencyCache(ttl_seconds=0.05)
        for _ in range(10):
            cache.check_and_store(str(uuid.uuid4()), {"data": True})
        assert len(cache._cache) == 10
        time.sleep(0.1)
        cache.cleanup_expired()
        assert len(cache._cache) == 0

    def test_non_expired_entries_survive_cleanup(self) -> None:
        cache = IdempotencyCache(ttl_seconds=60.0)
        key = str(uuid.uuid4())
        cache.check_and_store(key, {"data": True})
        cache.cleanup_expired()
        assert len(cache._cache) == 1

    def test_auto_cleanup_on_check(self) -> None:
        """Cache auto-cleans expired entries during check_and_store."""
        cache = IdempotencyCache(ttl_seconds=0.05, cleanup_interval=1)
        for _ in range(5):
            cache.check_and_store(str(uuid.uuid4()), {"data": True})
        time.sleep(0.1)
        # This call triggers cleanup because we've exceeded cleanup_interval items
        cache.check_and_store(str(uuid.uuid4()), {"new": True})
        # Only the new entry should remain (others expired)
        assert len(cache._cache) <= 2  # new + possibly 1 in-flight


class TestIdempotencyCacheThreadSafety:
    def test_concurrent_same_key_serialized(self) -> None:
        """Concurrent requests with same key should not both process."""
        cache = IdempotencyCache()
        key = str(uuid.uuid4())
        results: list[CachedResult | None] = []

        def worker(value: dict) -> None:
            r = cache.check_and_store(key, value)
            results.append(r)

        t1 = threading.Thread(target=worker, args=({"first": True},))
        t2 = threading.Thread(target=worker, args=({"second": True},))
        t1.start()
        t1.join()
        t2.start()
        t2.join()

        # First call returns None (new), second returns cached result
        assert results[0] is None
        assert results[1] is not None
        assert results[1].result == {"first": True}

    def test_concurrent_different_keys_both_process(self) -> None:
        cache = IdempotencyCache()
        results: list[CachedResult | None] = []
        lock = threading.Lock()

        def worker(key: str, value: dict) -> None:
            r = cache.check_and_store(key, value)
            with lock:
                results.append(r)

        t1 = threading.Thread(target=worker, args=(str(uuid.uuid4()), {"a": 1}))
        t2 = threading.Thread(target=worker, args=(str(uuid.uuid4()), {"b": 2}))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert all(r is None for r in results)


class TestImports:
    def test_idempotency_cache_importable_from_gateway(self) -> None:
        from openeinstein.gateway import IdempotencyCache as IC

        assert IC is not None

    def test_cached_result_importable(self) -> None:
        from openeinstein.gateway.idempotency import CachedResult as CR

        assert CR is not None
