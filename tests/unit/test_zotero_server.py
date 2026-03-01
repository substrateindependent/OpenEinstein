"""Unit tests for Zotero connector normalization."""

from __future__ import annotations

from openeinstein.tools.zotero_server import ZoteroMCPServer


def test_normalize_item_extracts_authors_and_identifiers() -> None:
    payload = {
        "key": "ABCD1234",
        "version": 10,
        "data": {
            "itemType": "journalArticle",
            "title": "A field equation",
            "creators": [{"firstName": "Albert", "lastName": "Einstein"}],
            "date": "1915",
            "DOI": "10.1000/example",
            "url": "https://example.org/paper",
        },
    }
    normalized = ZoteroMCPServer._normalize_item(payload)
    assert normalized["key"] == "ABCD1234"
    assert normalized["item_type"] == "journalArticle"
    assert normalized["title"] == "A field equation"
    assert normalized["authors"] == ["Albert Einstein"]
    assert normalized["doi"] == "10.1000/example"
