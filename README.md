# OpenEinstein

OpenEinstein is a local-first AI research platform for reproducible theoretical-physics campaigns.

The core platform is domain-agnostic and safety-enforced. Domain specifics live in Campaign Packs under `campaign-packs/`.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest --tb=short -q
ruff check src/ tests/
mypy src/openeinstein/ --ignore-missing-imports

openeinstein --help
openeinstein config --validate --path configs/openeinstein.example.yaml
openeinstein eval list
openeinstein pack list
```

## Core Architecture Rules

- Route model selection through logical roles: `reasoning`, `generation`, `fast`, `embeddings`.
- Route tool execution through `ToolBus` abstractions (no direct MCP/subprocess calls in agent/campaign logic).
- Enforce machine policy through `configs/POLICY.json` at gateway boundaries.
- Keep physics-subfield logic out of core modules; put it in Campaign Packs.

## First Campaign Pack

- Pack path: `campaign-packs/modified-gravity-action-search/`
- Includes: campaign config, skills, templates, known-model eval fixture, literature seed, and docs.
- Validate and dry-run:

```bash
openeinstein config --validate --path campaign-packs/modified-gravity-action-search/campaign.yaml
pytest tests/integration/test_modified_gravity_pack.py --tb=short -q
```

## Documentation

- Architecture overview: `docs/ARCHITECTURE.md`
- Canonical subsystem docs: `docs/canonical/`
- Trust model: `docs/trust-model.md`
- Configuration reference: `docs/configuration-reference.md`
- Campaign Pack authoring guide: `docs/campaign-pack-authoring.md`

## Repository Layout

- `src/openeinstein/`: platform code (routing, tools, gateway, agents, campaigns, persistence, tracing, evals, CLI)
- `tests/`: unit, integration, and eval coverage
- `campaign-packs/`: installable campaign-specific research packs
- `configs/`: runtime configuration and machine-enforced policy files
- `docs/`: architecture, canonical references, audits, and build plans

## License

MIT
