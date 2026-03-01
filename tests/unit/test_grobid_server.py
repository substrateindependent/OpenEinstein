"""Unit tests for GROBID server parsing helpers."""

from __future__ import annotations

from openeinstein.tools.grobid_server import GrobidMCPServer


def test_parse_tei_extracts_title_references_and_text() -> None:
    tei = """<TEI xmlns=\"http://www.tei-c.org/ns/1.0\">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>Sample Paper</title></titleStmt>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <p>First paragraph.</p>
      <p>Second paragraph.</p>
    </body>
    <back>
      <listBibl>
        <biblStruct/><biblStruct/>
      </listBibl>
    </back>
  </text>
</TEI>"""
    parsed = GrobidMCPServer._parse_tei(tei)
    assert parsed["title"] == "Sample Paper"
    assert parsed["references_count"] == 2
    assert "First paragraph." in parsed["text"]


def test_safe_name_normalizes_filename() -> None:
    assert GrobidMCPServer._safe_name("paper:1/2") == "paper_1_2"
