"""Unit tests for literature agent ranking and BibTeX output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openeinstein.agents import LiteratureAgent
from openeinstein.routing import ModelRouter, RoutingConfig
from openeinstein.tools import InMemoryToolServer, MCPConnectionManager, ToolBus


class MockSource:
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


def test_literature_agent_dedup_ranking_and_bibtex(tmp_path: Path) -> None:
    source_a = MockSource(
        "A",
        [
            {
                "title": "Paper A",
                "authors": ["Ada"],
                "year": 2020,
                "doi": "10.1000/a",
                "citation_count": 10,
                "references": ["r1"],
            },
            {
                "title": "Paper B",
                "authors": ["Ben"],
                "year": 2019,
                "doi": "10.1000/b",
                "citation_count": 2,
            },
        ],
    )
    source_b = MockSource(
        "B",
        [
            {
                "title": "Paper A",
                "authors": ["Ada"],
                "year": 2021,
                "doi": "10.1000/a",
                "citation_count": 12,
                "references": ["r2"],
            },
            {
                "title": "Paper C",
                "authors": ["Cal"],
                "year": 2018,
                "doi": "10.1000/c",
                "citation_count": 5,
            },
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
        sources=[source_a, source_b],
    )
    result = agent.run("literature", query="gravity", limit=5)
    records = result["records"]
    assert len(records) == 3
    assert records[0]["doi"] == "10.1000/a"
    assert records[0]["citation_count"] == 12
    assert sorted(records[0]["citation_chain"]) == ["r1", "r2"]
    assert result["bibtex"].count("@article{") == 3
