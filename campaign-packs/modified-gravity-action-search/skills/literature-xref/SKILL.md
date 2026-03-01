# literature-xref

Purpose: Link surviving candidates against prior literature and collect citation context.

## Inputs

- Candidate descriptors and reduced-equation fingerprints.
- Seed paper identifiers and query terms.

## Output Contract

- Ranked evidence list with provenance (`arxiv_id`, `doi`, title, relevance score).
- BibTeX snippet for cited references.
- Novelty notes (matches, partial overlaps, no-match evidence).

## Rules

- Never fabricate references; unresolved identifiers must remain unresolved.
- Keep source attribution with normalized IDs for every citation record.
