# stability-analysis

Purpose: Evaluate viability constraints and classify candidate stability outcomes.

## Inputs

- Perturbation diagnostics.
- Numeric scan configuration and thresholds.

## Output Contract

- Boolean viability label.
- Failure taxonomy (`tachyonic`, `ghost`, `superluminal`, `ill_conditioned`).
- Parameter subregions that satisfy constraints.

## Rules

- Classifications must be deterministic for fixed threshold settings.
- Provide explicit threshold metadata in every output payload.
