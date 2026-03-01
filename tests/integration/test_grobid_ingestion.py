"""Integration tests for GROBID ingestion server."""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest

from conftest import requires_docker, requires_network
from openeinstein.tools import GrobidMCPServer, MCPConnectionManager, ToolBus


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@requires_network
@requires_docker
def test_grobid_pdf_ingestion_roundtrip(tmp_path: Path) -> None:
    daemon_check = subprocess.run(["docker", "info"], check=False, capture_output=True)
    if daemon_check.returncode != 0:
        pytest.skip("Docker daemon is not running")

    pdf_path = tmp_path / "sample.pdf"
    request = Request("https://arxiv.org/pdf/1706.03762.pdf")
    with urlopen(request, timeout=45) as response:
        pdf_path.write_bytes(response.read())

    container_name = f"openeinstein-grobid-{uuid4().hex[:8]}"
    port = _free_port()
    server = GrobidMCPServer(
        tmp_path / "grobid",
        container_name=container_name,
        port=port,
    )

    manager = MCPConnectionManager()
    manager.register_server("grobid", server)
    bus = ToolBus(manager)

    started = bus.call("grobid", "start_service", {"timeout_seconds": 180})
    assert started.success

    try:
        ingested = bus.call(
            "grobid",
            "ingest_pdf",
            {"pdf_path": str(pdf_path), "timeout_seconds": 180},
        )
        assert ingested.success
        assert Path(ingested.output["tei_path"]).exists()
        assert ingested.output["references_count"] >= 0
    finally:
        bus.call("grobid", "stop_service", {"timeout_seconds": 60})
