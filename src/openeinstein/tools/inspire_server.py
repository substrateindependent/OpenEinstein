"""INSPIRE-HEP REST connector exposed as ToolBus server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec

_INSPIRE_BASE = "https://inspirehep.net/api"


class InspireSearchArgs(BaseModel):
    query: str = Field(min_length=1)
    size: int = Field(default=5, ge=1, le=25)
    page: int = Field(default=1, ge=1)
    timeout_seconds: float = Field(default=20.0, gt=0)


class InspireCitationArgs(BaseModel):
    record_id: str = Field(min_length=1)
    size: int = Field(default=10, ge=1, le=50)
    timeout_seconds: float = Field(default=20.0, gt=0)


class InspireMCPServer:
    """ToolBus-compatible INSPIRE connector."""

    def __init__(self, workspace: str | Path = ".openeinstein/inspire") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="search_literature", description="Search INSPIRE literature"),
            ToolSpec(name="lookup_author", description="Lookup INSPIRE author records"),
            ToolSpec(name="export_citations", description="Export citation records for INSPIRE paper"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("INSPIRE server not started")

        if tool_name == "search_literature":
            search_args = InspireSearchArgs.model_validate(args)
            payload = self._get_json(
                "/literature",
                {"q": search_args.query, "size": search_args.size, "page": search_args.page},
                search_args.timeout_seconds,
            )
            hits = self._extract_hits(payload)
            return {
                "query": search_args.query,
                "count": len(hits),
                "records": [self._normalize_literature_hit(hit) for hit in hits],
            }

        if tool_name == "lookup_author":
            search_args = InspireSearchArgs.model_validate(args)
            payload = self._get_json(
                "/authors",
                {"q": search_args.query, "size": search_args.size, "page": search_args.page},
                search_args.timeout_seconds,
            )
            hits = self._extract_hits(payload)
            return {
                "query": search_args.query,
                "count": len(hits),
                "records": [self._normalize_author_hit(hit) for hit in hits],
            }

        if tool_name == "export_citations":
            citation_args = InspireCitationArgs.model_validate(args)
            payload = self._get_json(
                "/literature",
                {"q": f"refersto:recid:{citation_args.record_id}", "size": citation_args.size},
                citation_args.timeout_seconds,
            )
            hits = self._extract_hits(payload)
            return {
                "record_id": citation_args.record_id,
                "count": len(hits),
                "citations": [self._normalize_literature_hit(hit) for hit in hits],
            }

        if tool_name == "capabilities":
            return {
                "backend": "inspire-hep",
                "capabilities": [
                    "literature_search",
                    "author_lookup",
                    "citation_export",
                    "metadata_normalization",
                ],
            }

        raise ToolBusError(f"Unknown INSPIRE tool: {tool_name}")

    @staticmethod
    def _get_json(endpoint: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
        query = urlencode(params)
        request = Request(
            f"{_INSPIRE_BASE}{endpoint}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "OpenEinstein/0.1 (+https://github.com/open-einstein/openeinstein)",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ToolBusError(f"INSPIRE HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ToolBusError(f"INSPIRE network error: {exc.reason}") from exc

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ToolBusError("INSPIRE response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ToolBusError("Unexpected INSPIRE payload shape")
        return payload

    @staticmethod
    def _extract_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
        hits = payload.get("hits", {})
        if not isinstance(hits, dict):
            return []
        rows = hits.get("hits", [])
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _normalize_literature_hit(hit: dict[str, Any]) -> dict[str, Any]:
        metadata = hit.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        titles = metadata.get("titles", [])
        title = ""
        if isinstance(titles, list) and titles and isinstance(titles[0], dict):
            title = str(titles[0].get("title", "")).strip()
        if not title:
            title = str(metadata.get("title", "")).strip()

        authors = metadata.get("authors", [])
        normalized_authors: list[str] = []
        if isinstance(authors, list):
            for author in authors:
                if isinstance(author, dict):
                    name = str(author.get("full_name", "")).strip()
                    if name:
                        normalized_authors.append(name)

        dois = metadata.get("dois", [])
        doi = ""
        if isinstance(dois, list) and dois and isinstance(dois[0], dict):
            doi = str(dois[0].get("value", "")).strip()

        return {
            "record_id": str(hit.get("id", "")),
            "title": title,
            "authors": normalized_authors,
            "citation_count": int(metadata.get("citation_count", 0) or 0),
            "doi": doi,
            "arxiv_eprints": metadata.get("arxiv_eprints", []),
            "updated": str(hit.get("updated", "")),
        }

    @staticmethod
    def _normalize_author_hit(hit: dict[str, Any]) -> dict[str, Any]:
        metadata = hit.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        name_value = metadata.get("name", {})
        if isinstance(name_value, dict):
            author_name = str(name_value.get("value", "")).strip()
        else:
            author_name = str(name_value).strip()
        return {
            "record_id": str(hit.get("id", "")),
            "name": author_name,
            "positions": metadata.get("positions", []),
            "ids": metadata.get("ids", []),
            "updated": str(hit.get("updated", "")),
        }
