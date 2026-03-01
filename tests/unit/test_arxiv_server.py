"""Unit tests for arXiv server normalization logic."""

from __future__ import annotations

import pytest

from openeinstein.tools.arxiv_server import ArxivMCPServer
from openeinstein.tools.tool_bus import ToolBusError


def test_parse_atom_feed_normalizes_expected_fields() -> None:
    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2501.00001v2</id>
    <updated>2025-01-03T12:00:00Z</updated>
    <published>2025-01-01T00:00:00Z</published>
    <title> A test title </title>
    <summary> A test summary. </summary>
    <author><name>Alice</name></author>
    <author><name>Bob</name></author>
    <link rel="related" type="application/pdf" href="https://arxiv.org/pdf/2501.00001v2.pdf" />
  </entry>
</feed>
"""
    records = ArxivMCPServer._parse_atom_feed(xml_payload)
    assert len(records) == 1
    record = records[0]
    assert record["arxiv_id"] == "2501.00001v2"
    assert record["title"] == "A test title"
    assert record["authors"] == ["Alice", "Bob"]
    assert record["pdf_url"] == "https://arxiv.org/pdf/2501.00001v2.pdf"


def test_validate_filename_blocks_paths() -> None:
    with pytest.raises(ToolBusError):
        ArxivMCPServer._validate_filename("../bad.pdf")
