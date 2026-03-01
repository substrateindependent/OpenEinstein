# action-taxonomy

Purpose: Generate a structured basis of modified-gravity action candidates.

## Inputs

- Symmetry assumptions (homogeneous/isotropic background).
- Allowed operator classes (scalar-tensor, higher-curvature, effective terms).
- Dimensional truncation order.

## Output Contract

- `candidate_key`: stable identifier.
- `action_expression`: symbolic action definition.
- `metadata`: operator family, EFT order, and region tags.

## Rules

- Prefer canonical basis terms to avoid equivalent duplicate candidates.
- Keep generated expressions backend-agnostic; backend-specific rendering happens via templates.
