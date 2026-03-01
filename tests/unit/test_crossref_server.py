"""Unit tests for CrossRef connector normalization."""

from __future__ import annotations

from openeinstein.tools.crossref_server import CrossrefMCPServer


def test_normalize_record_extracts_fields() -> None:
    payload = {
        "DOI": "10.1038/nphys1170",
        "title": ["Measured measurement"],
        "author": [{"given": "S", "family": "Haroche"}],
        "issued": {"date-parts": [[2008, 11, 2]]},
        "publisher": "Springer",
        "type": "journal-article",
        "URL": "https://doi.org/10.1038/nphys1170",
    }
    normalized = CrossrefMCPServer._normalize_record(payload)
    assert normalized["doi"] == "10.1038/nphys1170"
    assert normalized["title"] == "Measured measurement"
    assert normalized["authors"] == ["S Haroche"]
    assert normalized["year"] == 2008
