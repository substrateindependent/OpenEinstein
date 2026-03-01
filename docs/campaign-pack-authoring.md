# Campaign Pack Authoring Guide

Campaign Packs provide domain-specific research logic on top of OpenEinstein core.

## Principles

1. Keep core platform generic.
2. Put field-specific heuristics in `campaign-packs/<pack-name>/`.
3. Route all tools through ToolBus-backed interfaces.
4. Use backend capability declarations, not hardcoded backend names in campaign logic.

## Required Layout

```text
campaign-packs/<pack-name>/
  campaign.yaml
  skills/
    <skill-name>/SKILL.md
  templates/
    <template>.yaml
  evals/
    <suite>.yaml
  docs/
    README.md
    provenance.md
  literature-seed.yaml
```

## `campaign.yaml` Essentials

Required sections:

1. `campaign.name`
2. `campaign.version`
3. `campaign.search_space.generator_skill`
4. `campaign.gate_pipeline[]`

Recommended:

1. `campaign.dependencies.tools`
2. Per-gate `cas_requirements`
3. Per-gate `timeout_seconds`

## Skill Contracts

Each gate skill should define:

1. Purpose
2. Inputs
3. Output contract
4. Deterministic rules

Keep outputs typed and explicit so gate runners and evaluators can validate behavior.

## Template Contracts

Template files should include:

1. `template.template_id`
2. `template.version`
3. `template.backends[]`
4. Backend `body` with explicit placeholders (e.g., `{{action_expression}}`)

Provide at least one primary backend and optional fallbacks.

## Eval Fixtures

Include pack-specific eval suites in `evals/` for:

1. Known-model truth tables
2. Regression behavior for key gate outcomes
3. Failure-mode classification checks

## Validation Workflow

```bash
openeinstein config --validate --path campaign-packs/<pack-name>/campaign.yaml
pytest tests/integration/test_modified_gravity_pack.py --tb=short -q
```

## Packaging and Discovery

Packs are discovered from `campaign-packs/`:

```bash
openeinstein pack list
```

Install local pack copies with:

```bash
openeinstein pack install /path/to/pack
```
