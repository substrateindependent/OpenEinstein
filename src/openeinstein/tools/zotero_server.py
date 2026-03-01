"""Zotero REST connector exposed as ToolBus server."""

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

_ZOTERO_BASE = "https://api.zotero.org"


class ZoteroSyncArgs(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    timeout_seconds: float = Field(default=20.0, gt=0)


class ZoteroBibtexArgs(BaseModel):
    item_keys: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=20.0, gt=0)


class ZoteroMCPServer:
    """ToolBus-compatible Zotero connector."""

    def __init__(self, workspace: str | Path = ".openeinstein/zotero") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False
        self._api_key = os.getenv("ZOTERO_API_KEY", "").strip()
        self._user_id = os.getenv("ZOTERO_USER_ID", "").strip()

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="sync_library", description="Sync Zotero user library items"),
            ToolSpec(name="export_bibtex", description="Export Zotero items as BibTeX"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("Zotero server not started")
        if not self._api_key or not self._user_id:
            raise ToolBusError("ZOTERO_API_KEY and ZOTERO_USER_ID are required")

        if tool_name == "sync_library":
            sync_args = ZoteroSyncArgs.model_validate(args)
            items = self._list_items(limit=sync_args.limit, timeout=sync_args.timeout_seconds)
            records = [self._normalize_item(item) for item in items]
            return {"count": len(records), "records": records}

        if tool_name == "export_bibtex":
            bib_args = ZoteroBibtexArgs.model_validate(args)
            keys = [key.strip() for key in bib_args.item_keys if key.strip()]
            if not keys:
                return {"count": 0, "bibtex": ""}
            bibtex = self._export_bibtex(keys, timeout=bib_args.timeout_seconds)
            return {"count": len(keys), "bibtex": bibtex}

        if tool_name == "capabilities":
            return {
                "backend": "zotero",
                "capabilities": ["library_sync", "bibtex_export", "metadata_normalization"],
                "api_key_configured": bool(self._api_key),
                "user_id_configured": bool(self._user_id),
            }

        raise ToolBusError(f"Unknown Zotero tool: {tool_name}")

    def _list_items(self, *, limit: int, timeout: float) -> list[dict[str, Any]]:
        payload = self._api_get_json(
            f"/users/{self._user_id}/items",
            {"limit": limit, "format": "json"},
            timeout=timeout,
        )
        if not isinstance(payload, list):
            raise ToolBusError("Unexpected Zotero list payload")
        return [row for row in payload if isinstance(row, dict)]

    def _export_bibtex(self, item_keys: list[str], *, timeout: float) -> str:
        params = {"format": "bibtex", "itemKey": ",".join(item_keys)}
        return self._api_get_text(f"/users/{self._user_id}/items", params, timeout=timeout)

    def _api_get_json(self, path: str, params: dict[str, Any], timeout: float) -> Any:
        body = self._api_get_text(path, params, timeout=timeout)
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise ToolBusError("Zotero response was not valid JSON") from exc

    def _api_get_text(self, path: str, params: dict[str, Any], timeout: float) -> str:
        query = urlencode(params)
        url = f"{_ZOTERO_BASE}{path}?{query}"
        request = Request(
            url,
            headers={
                "Zotero-API-Key": self._api_key,
                "User-Agent": "OpenEinstein/0.1 (+https://github.com/open-einstein/openeinstein)",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            raise ToolBusError(f"Zotero HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ToolBusError(f"Zotero network error: {exc.reason}") from exc

    @staticmethod
    def _normalize_item(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", {})
        if not isinstance(data, dict):
            data = {}
        creators = data.get("creators", [])
        authors: list[str] = []
        if isinstance(creators, list):
            for creator in creators:
                if isinstance(creator, dict):
                    first = str(creator.get("firstName", "")).strip()
                    last = str(creator.get("lastName", "")).strip()
                    name = " ".join(part for part in [first, last] if part).strip()
                    if name:
                        authors.append(name)
        return {
            "key": str(payload.get("key", "")).strip(),
            "version": payload.get("version"),
            "item_type": str(data.get("itemType", "")).strip(),
            "title": str(data.get("title", "")).strip(),
            "authors": authors,
            "date": str(data.get("date", "")).strip(),
            "doi": str(data.get("DOI", "")).strip(),
            "url": str(data.get("url", "")).strip(),
        }
