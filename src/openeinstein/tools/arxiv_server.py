"""arXiv-backed MCP-style server using the public Atom API."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field, model_validator

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec

_ARXIV_ATOM_API = "https://export.arxiv.org/api/query"


class ArxivSearchArgs(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(default=5, ge=1, le=25)
    start: int = Field(default=0, ge=0)
    timeout_seconds: float = Field(default=20.0, gt=0)


class ArxivDownloadArgs(BaseModel):
    arxiv_id: str | None = None
    pdf_url: str | None = None
    destination_filename: str | None = None
    timeout_seconds: float = Field(default=45.0, gt=0)

    @model_validator(mode="after")
    def _validate_target(self) -> ArxivDownloadArgs:
        if not self.arxiv_id and not self.pdf_url:
            raise ValueError("Either arxiv_id or pdf_url must be provided")
        return self


class ArxivMCPServer:
    """ToolBus-compatible arXiv integration."""

    def __init__(self, workspace: str | Path = ".openeinstein/arxiv") -> None:
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
            ToolSpec(name="search", description="Search arXiv papers"),
            ToolSpec(name="download_pdf", description="Download arXiv PDF"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("arXiv server not started")

        if tool_name == "search":
            search_args = ArxivSearchArgs.model_validate(args)
            query = urlencode(
                {
                    "search_query": f"all:{search_args.query}",
                    "start": search_args.start,
                    "max_results": search_args.max_results,
                }
            )
            payload = self._http_get(
                f"{_ARXIV_ATOM_API}?{query}", timeout=search_args.timeout_seconds
            )
            records = self._parse_atom_feed(payload.decode("utf-8"))
            return {
                "query": search_args.query,
                "start": search_args.start,
                "max_results": search_args.max_results,
                "records": records,
                "count": len(records),
            }

        if tool_name == "download_pdf":
            download_args = ArxivDownloadArgs.model_validate(args)
            pdf_url = download_args.pdf_url or self._pdf_url_from_id(str(download_args.arxiv_id))
            content = self._http_get(pdf_url, timeout=download_args.timeout_seconds)
            filename = download_args.destination_filename or f"{self._safe_filename_from_url(pdf_url)}.pdf"
            destination = self._workspace / self._validate_filename(filename)
            destination.write_bytes(content)
            return {
                "path": str(destination),
                "size_bytes": destination.stat().st_size,
                "pdf_url": pdf_url,
            }

        if tool_name == "capabilities":
            return {
                "backend": "arxiv",
                "capabilities": [
                    "search",
                    "metadata_normalization",
                    "pdf_download",
                ],
            }

        raise ToolBusError(f"Unknown arXiv tool: {tool_name}")

    @staticmethod
    def _http_get(url: str, timeout: float) -> bytes:
        request = Request(
            url,
            headers={"User-Agent": "OpenEinstein/0.1 (+https://github.com/open-einstein/openeinstein)"},
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            raise ToolBusError(f"HTTP error from arXiv endpoint: {exc.code}") from exc
        except URLError as exc:
            raise ToolBusError(f"Network error calling arXiv endpoint: {exc.reason}") from exc

    @staticmethod
    def _parse_atom_feed(xml_payload: str) -> list[dict[str, Any]]:
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(xml_payload)
        entries: list[dict[str, Any]] = []
        for entry in root.findall("atom:entry", namespace):
            abs_url = (entry.findtext("atom:id", default="", namespaces=namespace) or "").strip()
            title = (entry.findtext("atom:title", default="", namespaces=namespace) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=namespace) or "").strip()
            published = (
                entry.findtext("atom:published", default="", namespaces=namespace) or ""
            ).strip()
            updated = (entry.findtext("atom:updated", default="", namespaces=namespace) or "").strip()

            authors = [
                (author.findtext("atom:name", default="", namespaces=namespace) or "").strip()
                for author in entry.findall("atom:author", namespace)
            ]

            arxiv_id = ArxivMCPServer._extract_arxiv_id(abs_url)
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else ""
            for link in entry.findall("atom:link", namespace):
                rel = link.attrib.get("rel", "")
                type_value = link.attrib.get("type", "")
                href = link.attrib.get("href", "")
                if rel == "related" and type_value == "application/pdf" and href:
                    pdf_url = href.strip()
                    break

            entries.append(
                {
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "authors": [name for name in authors if name],
                    "summary": summary,
                    "published": published,
                    "updated": updated,
                    "abs_url": abs_url,
                    "pdf_url": pdf_url,
                }
            )
        return entries

    @staticmethod
    def _extract_arxiv_id(abs_url: str) -> str:
        value = abs_url.rstrip("/").split("/")[-1]
        return value.strip()

    @staticmethod
    def _pdf_url_from_id(arxiv_id: str) -> str:
        cleaned = arxiv_id.strip()
        if not cleaned:
            raise ToolBusError("arxiv_id cannot be empty")
        return f"https://arxiv.org/pdf/{cleaned}.pdf"

    @staticmethod
    def _safe_filename_from_url(url: str) -> str:
        tail = url.rstrip("/").split("/")[-1].replace(".pdf", "")
        return re.sub(r"[^A-Za-z0-9._-]+", "_", tail).strip("._") or "paper"

    @staticmethod
    def _validate_filename(filename: str) -> str:
        if "/" in filename or "\\" in filename:
            raise ToolBusError("destination_filename must be a file name, not a path")
        return filename
