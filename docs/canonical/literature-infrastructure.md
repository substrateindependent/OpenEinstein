# Literature Infrastructure

## Purpose

Defines the canonical interfaces and invariants for literature discovery, metadata normalization, citation extraction, and publishing pipelines.

## Core Interfaces

- Literature tool servers expose structured search and fetch operations through ToolBus.
- Connector outputs normalize into typed records with stable keys (title, authors, identifiers, URLs, timestamps).
- Downstream consumers (agents, report generation, campaign packs) depend on normalized interfaces, not raw provider payloads.
- Export utilities produce BibTeX/BibLaTeX and citation chains from normalized records.

## Invariants

- All literature external calls are routed through ToolBus servers/connectors.
- Connectors never leak provider-specific payload shapes across module boundaries.
- Network and key requirements are represented via explicit integration tests and skip markers.
- Campaign-specific ranking heuristics stay in `campaign-packs/`; core remains domain-agnostic.
