"""Unit tests for ADS connector normalization."""

from __future__ import annotations

from openeinstein.tools.ads_server import ADSMCPServer


def test_normalize_search_doc_extracts_primary_fields() -> None:
    doc = {
        "bibcode": "2004qugr.book.....R",
        "title": ["Quantum Gravity"],
        "author": ["Rovelli, Carlo"],
        "year": "2004",
        "citation_count": 1679,
        "doi": ["10.1017/CBO9780511755804"],
    }
    normalized = ADSMCPServer._normalize_search_doc(doc)
    assert normalized["bibcode"] == "2004qugr.book.....R"
    assert normalized["title"] == "Quantum Gravity"
    assert normalized["authors"] == ["Rovelli, Carlo"]
    assert normalized["citation_count"] == 1679
    assert normalized["doi"] == "10.1017/CBO9780511755804"


def test_normalize_metrics_extracts_counts() -> None:
    payload = {
        "basic stats": {"number of papers": 1, "total number of reads": 201},
        "citation stats": {"total number of citations": 1598, "number of citing papers": 1598},
    }
    normalized = ADSMCPServer._normalize_metrics(payload)
    assert normalized["paper_count"] == 1
    assert normalized["total_reads"] == 201
    assert normalized["total_citations"] == 1598
    assert normalized["citing_papers"] == 1598
