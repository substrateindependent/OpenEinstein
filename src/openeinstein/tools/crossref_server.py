"""CrossRef REST connector exposed as ToolBus server."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec

_CROSSREF_BASE = "https://api.crossref.org"


class CrossrefDOIArgs(BaseModel):
    doi: str = Field(min_length=1)
    timeout_seconds: float = Field(default=20.0, gt=0)


class CrossrefSearchArgs(BaseModel):
    query: str = Field(min_length=1)
    rows: int = Field(default=5, ge=1, le=25)
    timeout_seconds: float = Field(default=20.0, gt=0)


class CrossrefMCPServer:
    """ToolBus-compatible CrossRef connector."""

    def __init__(self, workspace: str | Path = ".openeinstein/crossref") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False
        self._mailto = os.getenv("CROSSREF_MAILTO", "").strip()

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="resolve_doi", description="Resolve DOI metadata via CrossRef"),
            ToolSpec(name="search_works", description="Search CrossRef works"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("CrossRef server not started")

        if tool_name == "resolve_doi":
            doi_args = CrossrefDOIArgs.model_validate(args)
            encoded_doi = quote(doi_args.doi, safe="")
            payload = self._api_get(
                f"/works/{encoded_doi}", params=None, timeout=doi_args.timeout_seconds
            )
            message = payload.get("message", {})
            if not isinstance(message, dict):
                raise ToolBusError("Unexpected CrossRef DOI payload")
            return {"record": self._normalize_record(message)}

        if tool_name == "search_works":
            search_args = CrossrefSearchArgs.model_validate(args)
            payload = self._api_get(
                "/works",
                {"query": search_args.query, "rows": search_args.rows},
                timeout=search_args.timeout_seconds,
            )
            message = payload.get("message", {})
            if not isinstance(message, dict):
                raise ToolBusError("Unexpected CrossRef search payload")
            items = message.get("items", [])
            if not isinstance(items, list):
                items = []
            records = [self._normalize_record(item) for item in items if isinstance(item, dict)]
            return {"query": search_args.query, "count": len(records), "records": records}

        if tool_name == "capabilities":
            return {
                "backend": "crossref",
                "capabilities": ["doi_resolution", "work_search", "metadata_normalization"],
                "mailto_configured": bool(self._mailto),
            }

        raise ToolBusError(f"Unknown CrossRef tool: {tool_name}")

    def _api_get(self, path: str, params: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
        if params:
            query = urlencode(params)
            url = f"{_CROSSREF_BASE}{path}?{query}"
        else:
            url = f"{_CROSSREF_BASE}{path}"
        if self._mailto:
            suffix = "&" if "?" in url else "?"
            url = f"{url}{suffix}mailto={quote(self._mailto, safe='')}"

        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "OpenEinstein/0.1 (+https://github.com/open-einstein/openeinstein)",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ToolBusError(f"CrossRef HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ToolBusError(f"CrossRef network error: {exc.reason}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ToolBusError("CrossRef response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ToolBusError("Unexpected CrossRef payload shape")
        return payload

    @staticmethod
    def _normalize_record(payload: dict[str, Any]) -> dict[str, Any]:
        titles = payload.get("title", [])
        title = ""
        if isinstance(titles, list) and titles:
            title = str(titles[0]).strip()
        elif isinstance(titles, str):
            title = titles.strip()

        authors = payload.get("author", [])
        normalized_authors: list[str] = []
        if isinstance(authors, list):
            for author in authors:
                if isinstance(author, dict):
                    given = str(author.get("given", "")).strip()
                    family = str(author.get("family", "")).strip()
                    full = " ".join(part for part in [given, family] if part).strip()
                    if full:
                        normalized_authors.append(full)

        published = payload.get("issued", {})
        year: int | None = None
        if isinstance(published, dict):
            date_parts = published.get("date-parts", [])
            if (
                isinstance(date_parts, list)
                and date_parts
                and isinstance(date_parts[0], list)
                and date_parts[0]
            ):
                first = date_parts[0][0]
                if isinstance(first, int):
                    year = first

        doi = str(payload.get("DOI", "")).strip()
        return {
            "doi": doi,
            "title": title,
            "authors": normalized_authors,
            "year": year,
            "publisher": str(payload.get("publisher", "")).strip(),
            "type": str(payload.get("type", "")).strip(),
            "url": str(payload.get("URL", "")).strip(),
        }
