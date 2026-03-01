# OpenEinstein

OpenEinstein is an open-source AI physicist agent platform for running reproducible research campaigns locally.

This repository is bootstrapped for the architecture described in `OpenEinstein-Implementation-Plan.md`, with setup conventions aligned to `Development Resources/Repo-Setup-Best-Practices.md`.

## Current Status

Phase 0 (repository bootstrap) scaffold is implemented:
- Python package layout for core platform subsystems
- CLI entrypoint and command groups
- Test harness and CI workflow
- Canonical docs, trust model, policy invariants, and persona seed
- Campaign pack and config scaffolding

## Tech Stack (Planned Baseline)

- Python 3.12+
- Pydantic + PydanticAI
- LiteLLM model routing
- MCP SDK integration
- Typer CLI
- SQLite persistence
- OpenTelemetry-compatible tracing

## Quickstart

1. Create a Python 3.12+ virtual environment.
2. Install editable package:

```bash
python -m pip install -e ".[dev]"
```

3. Run tests:

```bash
pytest
```

4. View CLI help:

```bash
openeinstein --help
```

## Repository Overview

- `src/openeinstein/`: platform code (gateway, routing, tools, campaigns, tracing, security, CLI)
- `tests/`: unit, integration, eval, and campaign test suites
- `campaign-packs/`: installable campaign pack content bundles
- `configs/`: example runtime config and machine-enforced policy
- `docs/`: canonical docs, plans, architecture, decisions, and audits

## Design Constraints

- No hardcoded model names in implementation code. Use logical model roles.
- No direct provider API calls from features/agents. Route through framework abstractions.
- All tool access routes through the ToolBus abstraction.
- Safety constraints are machine-enforced by `configs/POLICY.json`.

## License

MIT
