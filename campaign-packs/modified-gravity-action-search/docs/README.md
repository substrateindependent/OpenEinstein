# Modified Gravity Action Search Pack

First production campaign pack for OpenEinstein theoretical modified-gravity screening.

## Included

- `campaign.yaml`: campaign definition with gate requirements and tool dependencies
- `skills/`: gate-level skill contracts for generation/reduction/analysis/xref
- `templates/`: backend-aware symbolic templates (Mathematica + SymPy fallbacks)
- `evals/known-models.yaml`: truth-table style fixtures for expected gate outcomes
- `literature-seed.yaml`: seed identifiers for reproducible literature bootstrap

## Usage

1. Validate config: `openeinstein config --validate --path campaign-packs/modified-gravity-action-search/campaign.yaml`
2. Dry-run pack checks with tests: `pytest tests/integration/test_modified_gravity_pack.py -q`
3. Run campaign via CLI orchestration once Phase 7 runner wiring is complete.
