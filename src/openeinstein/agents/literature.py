"""Literature-focused agent with deterministic merge/rank/citation handling."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from pydantic import BaseModel, Field

from openeinstein.agents.base import OpenEinsteinAgent


class LiteratureCandidate(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    citation_count: int = 0
    citation_chain: list[str] = Field(default_factory=list)
    source: str
    score: float = 0.0


class LiteratureRunResult(BaseModel):
    query: str
    records: list[LiteratureCandidate] = Field(default_factory=list)
    bibtex: str


class LiteratureSource(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[dict[str, Any]]: ...


CacheHook = Callable[[str, dict[str, Any]], None]


class LiteratureAgent(OpenEinsteinAgent):
    """Agent that merges results from multiple literature sources."""

    def __init__(
        self,
        *,
        sources: list[LiteratureSource],
        cache_hook: CacheHook | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._sources = sources
        self._cache_hook = cache_hook

    def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
        query = str(kwargs.get("query", "")).strip()
        limit = int(kwargs.get("limit", 10))
        if self._cache_hook:
            self._cache_hook("search_started", {"query": query, "limit": limit})

        merged: dict[str, LiteratureCandidate] = {}
        for source in self._sources:
            rows = source.search(query, limit)
            for row in rows:
                candidate = self._normalize_candidate(source.name, row)
                dedup_key = self._dedup_key(candidate)
                if dedup_key not in merged:
                    merged[dedup_key] = candidate
                else:
                    merged[dedup_key] = self._merge_candidates(merged[dedup_key], candidate)

        ranked = self._rank(list(merged.values()))[:limit]
        bibtex = self.to_bibtex(ranked)
        result = LiteratureRunResult(query=query, records=ranked, bibtex=bibtex)

        if self._cache_hook:
            self._cache_hook("search_finished", {"query": query, "count": len(ranked)})
        return result.model_dump()

    @staticmethod
    def _normalize_candidate(source_name: str, row: dict[str, Any]) -> LiteratureCandidate:
        authors = row.get("authors") or []
        citation_chain = row.get("citation_chain") or row.get("references") or []
        return LiteratureCandidate(
            title=str(row.get("title", "")),
            authors=[str(author) for author in authors],
            year=int(row["year"]) if row.get("year") is not None else None,
            doi=str(row["doi"]) if row.get("doi") else None,
            arxiv_id=str(row["arxiv_id"]) if row.get("arxiv_id") else None,
            url=str(row["url"]) if row.get("url") else None,
            citation_count=int(row.get("citation_count", 0)),
            citation_chain=[str(ref) for ref in citation_chain],
            source=source_name,
        )

    @staticmethod
    def _dedup_key(candidate: LiteratureCandidate) -> str:
        if candidate.doi:
            return f"doi:{candidate.doi.lower()}"
        if candidate.arxiv_id:
            return f"arxiv:{candidate.arxiv_id.lower()}"
        return f"title:{candidate.title.lower().strip()}"

    @staticmethod
    def _merge_candidates(
        left: LiteratureCandidate, right: LiteratureCandidate
    ) -> LiteratureCandidate:
        best = left if left.citation_count >= right.citation_count else right
        merged_chain = sorted(set(left.citation_chain + right.citation_chain))
        merged_authors = left.authors or right.authors
        return best.model_copy(
            update={
                "citation_chain": merged_chain,
                "authors": merged_authors,
                "source": f"{left.source},{right.source}",
            }
        )

    @staticmethod
    def _rank(candidates: list[LiteratureCandidate]) -> list[LiteratureCandidate]:
        ranked = sorted(
            candidates,
            key=lambda item: (
                -item.citation_count,
                -(item.year or 0),
                item.title.lower(),
            ),
        )
        for index, candidate in enumerate(ranked):
            ranked[index] = candidate.model_copy(update={"score": float(len(ranked) - index)})
        return ranked

    @staticmethod
    def to_bibtex(candidates: list[LiteratureCandidate]) -> str:
        entries: list[str] = []
        for candidate in candidates:
            key = (
                candidate.doi
                or candidate.arxiv_id
                or candidate.title.lower().replace(" ", "_")[:24]
            )
            authors = " and ".join(candidate.authors) if candidate.authors else "Unknown"
            year = candidate.year or 0
            doi = candidate.doi or ""
            url = candidate.url or ""
            entries.append(
                "\n".join(
                    [
                        f"@article{{{key},",
                        f"  title = {{{candidate.title}}},",
                        f"  author = {{{authors}}},",
                        f"  year = {{{year}}},",
                        f"  doi = {{{doi}}},",
                        f"  url = {{{url}}},",
                        "}",
                    ]
                )
            )
        return "\n\n".join(entries)
