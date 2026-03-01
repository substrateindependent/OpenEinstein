"""NASA ADS REST connector exposed as ToolBus server."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec

_ADS_BASE = "https://api.adsabs.harvard.edu/v1"


class ADSSearchArgs(BaseModel):
    query: str = Field(min_length=1)
    rows: int = Field(default=5, ge=1, le=25)
    timeout_seconds: float = Field(default=20.0, gt=0)
    fields: str = "bibcode,title,author,year,citation_count,doi"


class ADSMetricsArgs(BaseModel):
    bibcode: str = Field(min_length=1)
    timeout_seconds: float = Field(default=20.0, gt=0)


class ADSMCPServer:
    """ToolBus-compatible NASA ADS integration."""

    def __init__(self, workspace: str | Path = ".openeinstein/ads") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False
        self._api_key = os.getenv("ADS_API_KEY", "").strip()

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="search", description="Search ADS records"),
            ToolSpec(name="citation_metrics", description="Fetch ADS citation metrics by bibcode"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("ADS server not started")
        if not self._api_key:
            raise ToolBusError("ADS_API_KEY is not configured")

        if tool_name == "search":
            search_args = ADSSearchArgs.model_validate(args)
            payload = self._api_get(
                "/search/query",
                {
                    "q": search_args.query,
                    "rows": search_args.rows,
                    "fl": search_args.fields,
                },
                timeout=search_args.timeout_seconds,
            )
            response = payload.get("response", {})
            if not isinstance(response, dict):
                raise ToolBusError("Unexpected ADS search payload")
            docs = response.get("docs", [])
            if not isinstance(docs, list):
                docs = []
            records = [self._normalize_search_doc(doc) for doc in docs if isinstance(doc, dict)]
            return {
                "query": search_args.query,
                "count": len(records),
                "records": records,
            }

        if tool_name == "citation_metrics":
            metrics_args = ADSMetricsArgs.model_validate(args)
            payload = self._api_get(
                f"/metrics/{metrics_args.bibcode}",
                params=None,
                timeout=metrics_args.timeout_seconds,
            )
            return {"bibcode": metrics_args.bibcode, "metrics": self._normalize_metrics(payload)}

        if tool_name == "capabilities":
            return {
                "backend": "ads",
                "capabilities": [
                    "search",
                    "citation_metrics",
                    "metadata_normalization",
                ],
                "api_key_configured": bool(self._api_key),
            }

        raise ToolBusError(f"Unknown ADS tool: {tool_name}")

    def _api_get(self, path: str, params: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
        if params:
            query = urlencode(params)
            url = f"{_ADS_BASE}{path}?{query}"
        else:
            url = f"{_ADS_BASE}{path}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": "OpenEinstein/0.1 (+https://github.com/open-einstein/openeinstein)",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ToolBusError(f"ADS HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ToolBusError(f"ADS network error: {exc.reason}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ToolBusError("ADS response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ToolBusError("Unexpected ADS payload shape")
        return payload

    @staticmethod
    def _normalize_search_doc(doc: dict[str, Any]) -> dict[str, Any]:
        title_value = doc.get("title", [])
        title = ""
        if isinstance(title_value, list) and title_value:
            title = str(title_value[0]).strip()
        elif isinstance(title_value, str):
            title = title_value.strip()

        authors = doc.get("author", [])
        normalized_authors = [str(item).strip() for item in authors] if isinstance(authors, list) else []

        doi_value = doc.get("doi", [])
        doi = ""
        if isinstance(doi_value, list) and doi_value:
            doi = str(doi_value[0]).strip()
        elif isinstance(doi_value, str):
            doi = doi_value.strip()

        bibcode = str(doc.get("bibcode", "")).strip()
        return {
            "bibcode": bibcode,
            "title": title,
            "authors": [name for name in normalized_authors if name],
            "year": str(doc.get("year", "")).strip(),
            "citation_count": int(doc.get("citation_count", 0) or 0),
            "doi": doi,
            "url": f"https://ui.adsabs.harvard.edu/abs/{bibcode}/abstract" if bibcode else "",
        }

    @staticmethod
    def _normalize_metrics(payload: dict[str, Any]) -> dict[str, Any]:
        basic_stats = payload.get("basic stats", {})
        citation_stats = payload.get("citation stats", {})
        if not isinstance(basic_stats, dict):
            basic_stats = {}
        if not isinstance(citation_stats, dict):
            citation_stats = {}
        return {
            "paper_count": int(basic_stats.get("number of papers", 0) or 0),
            "total_reads": int(basic_stats.get("total number of reads", 0) or 0),
            "total_downloads": int(basic_stats.get("total number of downloads", 0) or 0),
            "total_citations": int(citation_stats.get("total number of citations", 0) or 0),
            "citing_papers": int(citation_stats.get("number of citing papers", 0) or 0),
        }
