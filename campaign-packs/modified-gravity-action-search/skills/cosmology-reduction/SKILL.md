# cosmology-reduction

Purpose: Reduce action candidates on FLRW background and derive background equations.

## Inputs

- Candidate action.
- Metric ansatz and matter content assumptions.

## Output Contract

- Reduced action / effective Lagrangian.
- Background equations (Friedmann-like system).
- Sanity flags for algebraic consistency.

## Rules

- Preserve symbolic provenance: keep intermediate expressions and assumptions.
- Emit deterministic failure reasons when reduction cannot be completed.
