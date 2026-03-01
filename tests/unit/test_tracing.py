"""Unit tests for tracing subsystem."""

from __future__ import annotations

from pathlib import Path

from openeinstein.persistence import CampaignDB
from openeinstein.tracing import TraceStore, set_default_trace_store, traced


def test_traced_function_persists_span(tmp_path: Path) -> None:
    store = TraceStore(CampaignDB(tmp_path / "trace.db"))
    set_default_trace_store(store)

    @traced("gate_check")
    def run_gate(*, run_id: str) -> str:
        return "ok"

    assert run_gate(run_id="run-trace") == "ok"
    spans = store.list_spans("run-trace")
    assert len(spans) == 1
    assert spans[0].span_name == "gate_check"
    assert spans[0].attributes["status"] == "ok"


def test_otlp_json_export_shape(tmp_path: Path) -> None:
    store = TraceStore(CampaignDB(tmp_path / "trace.db"))
    set_default_trace_store(store)

    @traced("step")
    def step(*, run_id: str) -> int:
        return 1

    _ = step(run_id="run-export")

    payload = store.export_otlp_json("run-export")
    assert "resourceSpans" in payload
    span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span["name"] == "step"
