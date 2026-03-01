"""Tracing primitives backed by SQLite persistence."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, cast

from openeinstein.persistence import CampaignDB, TraceSpanRecord

P = ParamSpec("P")


@dataclass(frozen=True)
class SpanEvent:
    run_id: str
    span_name: str
    attributes: dict[str, Any]
    started_at: str
    ended_at: str


class TraceStore:
    """Span storage and OTLP-compatible export."""

    def __init__(self, db: CampaignDB) -> None:
        self._db = db

    @classmethod
    def from_path(cls, db_path: str | Path) -> "TraceStore":
        return cls(CampaignDB(db_path))

    def record_span(
        self,
        run_id: str,
        span_name: str,
        attributes: dict[str, Any],
        started_at: str,
        ended_at: str,
    ) -> int:
        return self._db.add_trace_span(run_id, span_name, attributes, started_at, ended_at)

    def list_spans(self, run_id: str) -> list[TraceSpanRecord]:
        return self._db.get_trace_spans(run_id)

    def export_otlp_json(self, run_id: str) -> dict[str, Any]:
        spans = self.list_spans(run_id)
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "openeinstein"}},
                            {"key": "run.id", "value": {"stringValue": run_id}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "openeinstein.tracing"},
                            "spans": [
                                {
                                    "name": span.span_name,
                                    "startTimeUnixNano": span.started_at,
                                    "endTimeUnixNano": span.ended_at or span.started_at,
                                    "attributes": [
                                        {"key": key, "value": {"stringValue": str(value)}}
                                        for key, value in span.attributes.items()
                                    ],
                                }
                                for span in spans
                            ],
                        }
                    ],
                }
            ]
        }


_default_trace_store: TraceStore | None = None


def set_default_trace_store(store: TraceStore) -> None:
    global _default_trace_store
    _default_trace_store = store


def get_default_trace_store() -> TraceStore:
    global _default_trace_store
    if _default_trace_store is None:
        _default_trace_store = TraceStore.from_path(Path(".openeinstein") / "openeinstein.db")
    return _default_trace_store


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def traced(span_name: str) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Decorator that records span timing around sync/async functions."""

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                run_id = str(kwargs.get("run_id", "default"))
                started = _now_iso()
                store = get_default_trace_store()
                attrs = {"function": func.__qualname__}
                try:
                    result = await cast(Callable[P, Any], func)(*args, **kwargs)
                    attrs["status"] = "ok"
                    return result
                except Exception:
                    attrs["status"] = "error"
                    raise
                finally:
                    store.record_span(run_id, span_name, attrs, started, _now_iso())

            return cast(Callable[P, Any], async_wrapper)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            run_id = str(kwargs.get("run_id", "default"))
            started = _now_iso()
            store = get_default_trace_store()
            attrs = {"function": func.__qualname__}
            try:
                result = func(*args, **kwargs)
                attrs["status"] = "ok"
                return result
            except Exception:
                attrs["status"] = "error"
                raise
            finally:
                store.record_span(run_id, span_name, attrs, started, _now_iso())

        return sync_wrapper

    return decorator
