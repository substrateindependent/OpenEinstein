# perturbation-analysis

Purpose: Perform linear perturbation expansion and identify unstable mode signatures.

## Inputs

- Reduced equations from cosmology gate.
- Perturbation order and gauge assumptions.

## Output Contract

- Perturbed equations and mode coefficients.
- Constraint/propagating mode counts.
- Diagnostic flags (`ghost_risk`, `gradient_risk`, `strong_coupling_risk`).

## Rules

- Keep gauge choices explicit in output metadata.
- Failure output must distinguish algebraic issues from numerical instability.
