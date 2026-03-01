"""Unit tests for INSPIRE connector normalization."""

from __future__ import annotations

from openeinstein.tools.inspire_server import InspireMCPServer


def test_normalize_literature_hit_extracts_key_fields() -> None:
    hit = {
        "id": "812316",
        "updated": "2026-02-06T10:24:13.743591+00:00",
        "metadata": {
            "citation_count": 3,
            "authors": [{"full_name": "Hedrich, Reiner"}],
            "titles": [{"title": "Quantum gravity and X"}],
            "dois": [{"value": "10.1000/example"}],
            "arxiv_eprints": [{"value": "0901.1391"}],
        },
    }
    normalized = InspireMCPServer._normalize_literature_hit(hit)
    assert normalized["record_id"] == "812316"
    assert normalized["title"] == "Quantum gravity and X"
    assert normalized["authors"] == ["Hedrich, Reiner"]
    assert normalized["citation_count"] == 3
    assert normalized["doi"] == "10.1000/example"


def test_normalize_author_hit_extracts_name_and_id() -> None:
    hit = {
        "id": "1010907",
        "updated": "2023-09-14T06:26:42.844907+00:00",
        "metadata": {
            "name": {"value": "Einstein, Albert"},
            "ids": [{"schema": "INSPIRE ID", "value": "INSPIRE-00000020"}],
        },
    }
    normalized = InspireMCPServer._normalize_author_hit(hit)
    assert normalized["record_id"] == "1010907"
    assert normalized["name"] == "Einstein, Albert"
