"""Semantic Scholar-backed MCP-style server."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, model_validator

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec

_S2_BASE = "https://api.semanticscholar.org/graph/v1"
_DEFAULT_FIELDS = ",".join(
    [
        "paperId",
        "title",
        "year",
        "url",
        "citationCount",
        "referenceCount",
        "externalIds",
        "authors",
    ]
)


class SemanticScholarSearchArgs(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=25)
    offset: int = Field(default=0, ge=0)
    fields: str = _DEFAULT_FIELDS
    timeout_seconds: float = Field(default=20.0, gt=0)


class SemanticScholarPaperArgs(BaseModel):
    paper_id: str | None = None
    doi: str | None = None
    fields: str = _DEFAULT_FIELDS
    timeout_seconds: float = Field(default=20.0, gt=0)

    @model_validator(mode="after")
    def _validate_lookup_target(self) -> SemanticScholarPaperArgs:
        if not self.paper_id and not self.doi:
            raise ValueError("Either paper_id or doi must be provided")
        return self


class SemanticScholarMCPServer:
    """ToolBus-compatible Semantic Scholar integration."""

    def __init__(self, workspace: str | Path = ".openeinstein/semantic-scholar") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False
        self._api_key = os.getenv("S2_API_KEY", "").strip()

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="search", description="Search Semantic Scholar papers"),
            ToolSpec(name="get_paper", description="Fetch Semantic Scholar paper metadata"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("Semantic Scholar server not started")

        if tool_name == "search":
            search_args = SemanticScholarSearchArgs.model_validate(args)
            payload = self._api_get(
                "/paper/search",
                {
                    "query": search_args.query,
                    "limit": search_args.limit,
                    "offset": search_args.offset,
                    "fields": search_args.fields,
                },
                timeout=search_args.timeout_seconds,
            )
            rows = payload.get("data", []) if isinstance(payload, dict) else []
            normalized = [self._normalize_record(row) for row in rows if isinstance(row, dict)]
            return {
                "query": search_args.query,
                "count": len(normalized),
                "total": int(payload.get("total", len(normalized))) if isinstance(payload, dict) else 0,
                "records": normalized,
            }

        if tool_name == "get_paper":
            paper_args = SemanticScholarPaperArgs.model_validate(args)
            target = paper_args.paper_id or f"DOI:{paper_args.doi}"
            encoded = urlencode({"fields": paper_args.fields})
            payload = self._api_get(
                f"/paper/{target}?{encoded}",
                params=None,
                timeout=paper_args.timeout_seconds,
            )
            if not isinstance(payload, dict):
                raise ToolBusError("Unexpected Semantic Scholar payload")
            return {"paper": self._normalize_record(payload)}

        if tool_name == "capabilities":
            return {
                "backend": "semantic_scholar",
                "capabilities": [
                    "search",
                    "paper_lookup",
                    "citation_metrics",
                    "metadata_normalization",
                ],
                "api_key_configured": bool(self._api_key),
            }

        raise ToolBusError(f"Unknown Semantic Scholar tool: {tool_name}")

    def _api_get(
        self, path: str, params: dict[str, Any] | None, timeout: float
    ) -> dict[str, Any] | list[Any]:
        if params:
            query = urlencode(params)
            url = f"{_S2_BASE}{path}?{query}"
        else:
            url = f"{_S2_BASE}{path}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "OpenEinstein/0.1 (+https://github.com/open-einstein/openeinstein)",
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key

        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                content = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ToolBusError(f"Semantic Scholar HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ToolBusError(f"Semantic Scholar network error: {exc.reason}") from exc

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ToolBusError("Semantic Scholar response was not valid JSON") from exc

    @staticmethod
    def _normalize_record(payload: dict[str, Any]) -> dict[str, Any]:
        authors = payload.get("authors", [])
        normalized_authors = []
        if isinstance(authors, list):
            for author in authors:
                if isinstance(author, dict):
                    name = str(author.get("name", "")).strip()
                    if name:
                        normalized_authors.append(name)
                elif isinstance(author, str):
                    normalized_authors.append(author.strip())

        external_ids = payload.get("externalIds", {})
        if not isinstance(external_ids, dict):
            external_ids = {}

        return {
            "paper_id": str(payload.get("paperId", "")),
            "title": str(payload.get("title", "")).strip(),
            "year": payload.get("year"),
            "url": str(payload.get("url", "")).strip(),
            "citation_count": int(payload.get("citationCount", 0) or 0),
            "reference_count": int(payload.get("referenceCount", 0) or 0),
            "external_ids": external_ids,
            "authors": normalized_authors,
            "doi": str(external_ids.get("DOI", "")).strip(),
        }
