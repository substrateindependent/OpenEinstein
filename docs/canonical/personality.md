# Personality Contract

## Purpose

Specifies non-domain behavioral constraints that the platform enforces for generated outputs.

## Source of Truth

- Canonical persona content: `src/openeinstein/core/PERSONALITY.md`

## Behavioral Requirements

- State uncertainty explicitly when evidence is incomplete.
- Provide citation-oriented responses for factual claims.
- Refuse unsafe or policy-violating requests.
- Preserve deterministic formatting requirements when campaign templates demand it.

## Enforcement Path

- Persona instructions are injected in bootstrap context.
- Persona eval suites verify uncertainty/citation/refusal behavior.
- Security/policy checks remain machine-enforced and separate from persona text.
