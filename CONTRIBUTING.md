# Contributing to OpenEinstein

## Scope and Principles

OpenEinstein is built as a domain-agnostic core platform with domain-specific extensions delivered via Campaign Packs.

Before starting implementation work, read `BUILD-READY.md` and follow its verification loop, stop conditions, and commit discipline.

Before opening a PR, verify your changes preserve these constraints:
- No hardcoded model names in core logic
- No direct LLM provider calls from feature code
- All tool usage goes through ToolBus
- Safety invariants remain machine-enforced (policy + gateway), not prompt-only

## PR Size and Structure

- Target PR size: <= 500 net lines when possible.
- For larger work, split by task boundary (routing, persistence, tracing, etc.).
- Use one coherent concern per PR.
- Include tests and docs updates in the same PR.

## Campaign Pack-First Policy

If logic is specific to a physics subfield, model family, or campaign objective:
- Put it in a Campaign Pack under `campaign-packs/`
- Keep core modules generic and reusable
- Document pack provenance and assumptions

## Local Validation

Use Python 3.12+.

```bash
python -m pip install -e ".[dev]"
pytest
```

## CI Expectations

PRs must pass CI:
- Install succeeds
- Tests pass

## Documentation Requirements

Update these when relevant:
- `docs/ARCHITECTURE.md` for structural changes
- `docs/CHANGELOG.md` with dated entries
- `docs/canonical/*` when subsystem behavior changes
- `CLAUDE.md` and `AGENTS.md` when conventions or context rules change
