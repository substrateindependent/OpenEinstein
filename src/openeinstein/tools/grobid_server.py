"""GROBID Docker-backed wrapper exposed as ToolBus server."""

from __future__ import annotations

import mimetypes
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec


class StartServiceArgs(BaseModel):
    timeout_seconds: float = Field(default=120.0, gt=0)


class IngestPDFArgs(BaseModel):
    pdf_path: str
    timeout_seconds: float = Field(default=120.0, gt=0)


class StopServiceArgs(BaseModel):
    timeout_seconds: float = Field(default=30.0, gt=0)


class GrobidMCPServer:
    """ToolBus-compatible GROBID connector using Docker runtime."""

    def __init__(
        self,
        workspace: str | Path = ".openeinstein/grobid",
        *,
        container_name: str = "openeinstein-grobid",
        image: str = "lfoppiano/grobid:0.8.0",
        port: int = 8070,
    ) -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._container_name = container_name
        self._image = image
        self._port = port
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="start_service", description="Start GROBID Docker service"),
            ToolSpec(name="stop_service", description="Stop GROBID Docker service"),
            ToolSpec(name="ingest_pdf", description="Extract metadata/text/references from PDF"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("GROBID server not started")

        if tool_name == "start_service":
            start_args = StartServiceArgs.model_validate(args)
            self._ensure_service(timeout_seconds=start_args.timeout_seconds)
            return {"started": True, "port": self._port, "container": self._container_name}

        if tool_name == "stop_service":
            stop_args = StopServiceArgs.model_validate(args)
            self._stop_container(timeout_seconds=stop_args.timeout_seconds)
            return {"stopped": True, "container": self._container_name}

        if tool_name == "ingest_pdf":
            ingest_args = IngestPDFArgs.model_validate(args)
            self._ensure_service(timeout_seconds=min(ingest_args.timeout_seconds, 120.0))
            pdf_path = Path(ingest_args.pdf_path).expanduser().resolve()
            if not pdf_path.exists():
                raise ToolBusError(f"PDF file not found: {pdf_path}")
            tei = self._process_fulltext(pdf_path, timeout_seconds=ingest_args.timeout_seconds)
            parsed_tei = self._parse_tei(tei)
            artifact_name = f"{self._safe_name(pdf_path.stem)}-{uuid.uuid4().hex[:8]}.tei.xml"
            artifact_path = self._workspace / artifact_name
            artifact_path.write_text(tei, encoding="utf-8")
            return {
                "tei_path": str(artifact_path),
                "title": parsed_tei["title"],
                "references_count": parsed_tei["references_count"],
                "text": parsed_tei["text"],
            }

        if tool_name == "capabilities":
            return {
                "backend": "grobid",
                "capabilities": [
                    "pdf_ingestion",
                    "metadata_extraction",
                    "reference_extraction",
                    "tei_export",
                ],
            }

        raise ToolBusError(f"Unknown GROBID tool: {tool_name}")

    def _ensure_service(self, *, timeout_seconds: float) -> None:
        if self._is_container_running():
            self._wait_until_alive(timeout_seconds=timeout_seconds)
            return

        self._run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                self._container_name,
                "-p",
                f"{self._port}:8070",
                self._image,
            ],
            timeout=timeout_seconds,
        )
        self._wait_until_alive(timeout_seconds=timeout_seconds)

    def _stop_container(self, *, timeout_seconds: float) -> None:
        if not self._is_container_running():
            return
        self._run(["docker", "stop", self._container_name], timeout=timeout_seconds)

    def _is_container_running(self) -> bool:
        completed = self._run(
            [
                "docker",
                "ps",
                "--filter",
                f"name=^{self._container_name}$",
                "--format",
                "{{.Names}}",
            ],
            timeout=10,
        )
        return self._container_name in completed.stdout.strip().splitlines()

    def _wait_until_alive(self, *, timeout_seconds: float) -> None:
        deadline = time.time() + timeout_seconds
        last_error = ""
        while time.time() < deadline:
            try:
                request = Request(f"http://127.0.0.1:{self._port}/api/isalive")
                with urlopen(request, timeout=5) as response:
                    body = response.read().decode("utf-8").lower()
                if response.status == 200 and "true" in body:
                    return
            except (HTTPError, URLError, OSError) as exc:
                last_error = str(exc)
            time.sleep(1)
        raise ToolBusError(f"GROBID service did not become healthy: {last_error or 'timeout'}")

    def _process_fulltext(self, pdf_path: Path, *, timeout_seconds: float) -> str:
        boundary = f"----openeinstein-{uuid.uuid4().hex}"
        data = pdf_path.read_bytes()
        mime_type = mimetypes.guess_type(pdf_path.name)[0] or "application/pdf"

        parts = [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                'Content-Disposition: form-data; name="input"; filename="'
                + pdf_path.name
                + '"\r\n'
            ).encode("utf-8"),
            f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
            data,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
        body = b"".join(parts)
        request = Request(
            f"http://127.0.0.1:{self._port}/api/processFulltextDocument",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/xml",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            raise ToolBusError(f"GROBID HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ToolBusError(f"GROBID network error: {exc.reason}") from exc

    @staticmethod
    def _parse_tei(tei_xml: str) -> dict[str, Any]:
        root = ET.fromstring(tei_xml)
        title = ""
        title_node = root.find(".//{*}title")
        if title_node is not None and title_node.text:
            title = title_node.text.strip()

        paragraphs = []
        for paragraph in root.findall(".//{*}body//{*}p"):
            text = "".join(paragraph.itertext()).strip()
            if text:
                paragraphs.append(text)

        references_count = len(root.findall(".//{*}listBibl/{*}biblStruct"))
        return {
            "title": title,
            "references_count": references_count,
            "text": "\n\n".join(paragraphs),
        }

    @staticmethod
    def _safe_name(name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
        return cleaned or "document"

    @staticmethod
    def _run(command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode != 0:
            raise ToolBusError(completed.stderr.strip() or "Docker command failed")
        return completed
