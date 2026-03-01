"""Integration tests for literature agent cache hooks and output shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openeinstein.agents import LiteratureAgent
from openeinstein.routing import ModelRouter, RoutingConfig
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


class Source:
    def __init__(self, name: str, rows: list[dict[str, Any]]) -> None:
        self.name = name
        self._rows = rows

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:  # noqa: ARG002
        return self._rows[:limit]


def _router() -> ModelRouter:
    return ModelRouter(
        RoutingConfig.model_validate(
            {
                "model_routing": {
                    "roles": {
                        "reasoning": {
                            "description": "reasoning",
                            "default": {"provider": "p", "model": "m-r"},
                        },
                        "generation": {
                            "description": "generation",
                            "default": {"provider": "p", "model": "m-g"},
                        },
                        "fast": {
                            "description": "fast",
                            "default": {"provider": "p", "model": "m-f"},
                        },
                        "embeddings": {
                            "description": "embeddings",
                            "default": {"provider": "p", "model": "m-e"},
                        },
                    }
                }
            }
        )
    )


def _policy(path: Path) -> Path:
    target = path / "policy.json"
    target.write_text(
        json.dumps(
            {
                "version": "1.0",
                "invariants": {
                    "require_approval_for": [],
                    "max_llm_calls_per_step": 50,
                    "max_cas_timeout_minutes": 60,
                    "forbidden_operations": [],
                    "require_verification_after_gates": True,
                },
                "enforced_by": "gateway",
                "note": "test",
            }
        ),
        encoding="utf-8",
    )
    return target


def test_literature_agent_cache_hook_flow(tmp_path: Path) -> None:
    events: list[tuple[str, dict[str, Any]]] = []

    def cache_hook(event: str, payload: dict[str, Any]) -> None:
        events.append((event, payload))

    source = Source(
        "S",
        [
            {
                "title": "A",
                "authors": ["Author"],
                "year": 2024,
                "doi": "10.1000/x",
                "citation_count": 3,
            }
        ],
    )
    manager = MCPConnectionManager()
    manager.register_server("local", InMemoryToolServer({"noop": lambda args: args}))
    bus = ToolBus(manager)
    agent = LiteratureAgent(
        name="lit",
        model_role="generation",
        router=_router(),
        tool_bus=bus,
        policy_path=_policy(tmp_path),
        sources=[source],
        cache_hook=cache_hook,
    )

    result = agent.run("literature", query="q", limit=1)
    assert len(result["records"]) == 1
    assert result["records"][0]["title"] == "A"
    assert events[0][0] == "search_started"
    assert events[-1][0] == "search_finished"
