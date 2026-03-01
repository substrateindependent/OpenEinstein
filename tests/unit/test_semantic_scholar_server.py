"""Unit tests for Semantic Scholar server normalization."""

from __future__ import annotations

from openeinstein.tools.semantic_scholar_server import SemanticScholarMCPServer


def test_normalize_record_maps_fields() -> None:
    payload = {
        "paperId": "abc123",
        "title": "  A semantic paper  ",
        "year": 2024,
        "url": "https://example.org/paper",
        "citationCount": 17,
        "referenceCount": 5,
        "externalIds": {"DOI": "10.1000/example"},
        "authors": [{"name": "Alice"}, {"name": "Bob"}],
    }
    normalized = SemanticScholarMCPServer._normalize_record(payload)
    assert normalized["paper_id"] == "abc123"
    assert normalized["title"] == "A semantic paper"
    assert normalized["citation_count"] == 17
    assert normalized["reference_count"] == 5
    assert normalized["doi"] == "10.1000/example"
    assert normalized["authors"] == ["Alice", "Bob"]
