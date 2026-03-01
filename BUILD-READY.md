# OpenEinstein: Pre-Development Readiness Document

**Date:** 2026-03-01
**Purpose:** Freeze scope, environment, credentials, verification, and agent guardrails so that an AI coding agent can begin autonomous execution of the Implementation Plan without thrashing on unresolved decisions.

---

## 1. Core vs. Plugin Scope for First Green Build

The Implementation Plan describes a large surface area of tools. We maintain two test profiles:

- **Agent-local (primary):** The coding agent runs on the developer's machine with all system dependencies installed, all API keys populated, and network access enabled. **The agent should build and test real integrations — not stubs.** Skipping tests is a last resort, not the default.
- **CI-minimal (fallback):** GitHub Actions with no special system packages. Tests that require external services are skipped gracefully so CI stays green even when keys/tools aren't available.

The skip markers in `tests/conftest.py` exist as a safety net for CI, not as permission for the agent to skip work. When running locally, the agent should verify that integration tests actually execute (not skip).

### REQUIRED for CI (must pass in GitHub Actions with no special system deps)

| Component | Phase | Rationale |
|-----------|-------|-----------|
| Repository structure + `pip install -e ".[dev]"` | 0.1 | Build must install cleanly |
| CLAUDE.md, AGENTS.md, CONTRIBUTING.md | 0.2 | Agent context |
| Canonical docs index + core architecture doc | 0.3 | Living documentation |
| PERSONALITY.md + trust model | 0.4 | Persona and boundary definitions |
| POLICY.json (already exists) | 0.5 | Machine-enforced invariants |
| Model routing layer (with mock LLM calls) | 1.1 | Core abstraction — no real API keys needed for unit tests |
| Tool bus (MCP + CLI+JSON) with mock tools | 1.2 | Core abstraction — test with in-process mock MCP server |
| Persistence layer (SQLite) | 1.3 | Pure Python, no external deps |
| Tracing subsystem | 1.4 | Pure Python decorator + SQLite |
| Eval framework scaffolding | 1.5 | Pure Python runner + SQLite |
| Control plane primitives | 1.6 | Pure Python state machine |
| Campaign Registry MCP server | 1.7 | Wraps persistence; test with in-process MCP |
| Security subsystem (approvals, secrets, policy) | 2.1 | Pure Python |
| Hook system | 2.2 | Pure Python |
| Skill registry + base agent abstractions | 2.3 | Uses mock LLM (PydanticAI test mode) |
| Orchestrator agent (with stub subagents) | 2.4 | Mock LLM, mock tools |
| Computation agent (with mock CAS responses) | 2.5 | No real CAS needed |
| Literature agent (with mock API responses) | 2.6 | No real API calls needed |
| Verification agent (with mock data) | 2.7 | No real data needed |
| SymPy MCP server | 3.1 | Pure Python — always available |
| CAS template infrastructure | 3.4 | Pure Python template parsing |
| Parameter Scanner (NumPy/SciPy) | 3.5 | Already in core deps |
| Sandboxed Python runner | 3.6 | Process isolation, no Docker required for tests |
| Campaign config loader | 5.1 | Pure Python + Pydantic |
| Campaign state machine | 5.2 | Pure Python + SQLite |
| Gate pipeline runner (with mocks) | 5.3 | Mock CAS/tool responses |
| Adaptive sampling engine | 5.4 | Pure Python heuristics |
| CLI (all commands wired) | 6.1 | Typer — pure Python |
| Report generation | 6.2 | Pure Python |

### STUBBED — Interface exists, tests skipped when dependency absent

These components have full protocol/interface definitions and mock implementations in tests, but integration tests are marked `@pytest.mark.skipif` when the system dependency isn't installed.

| Component | Phase | System Dependency | Skip Condition |
|-----------|-------|-------------------|----------------|
| Mathematica MCP server | 3.2 | Wolfram Engine + xAct | `shutil.which("wolframscript") is None` |
| Cadabra MCP server | 3.3 | cadabra2 Python package | `importlib.util.find_spec("cadabra2") is None` |
| arXiv MCP server (real API) | 4.1 | Node.js + npx | `shutil.which("npx") is None` or network unavailable |
| Semantic Scholar MCP | 4.2 | S2_API_KEY env var | `os.getenv("S2_API_KEY") is None` |
| INSPIRE-HEP connector | 4.3 | Network access | `OPENEINSTEIN_SKIP_NETWORK_TESTS` env var |
| NASA ADS connector | 4.4 | ADS_API_KEY env var | `os.getenv("ADS_API_KEY") is None` |
| CrossRef MCP | 4.5 | Network access | `OPENEINSTEIN_SKIP_NETWORK_TESTS` env var |
| Zotero integration | 4.6 | ZOTERO_API_KEY env var | `os.getenv("ZOTERO_API_KEY") is None` |
| GROBID PDF ingestion | 4.7 | Docker + GROBID container | `shutil.which("docker") is None` |
| LaTeX publishing toolchain | 4.8 | latexmk + TeX distribution | `shutil.which("latexmk") is None` |
| PhysBERT embeddings | Optional | torch + transformers | `importlib.util.find_spec("torch") is None` |
| pgvector | Optional | PostgreSQL + pgvector ext | Only installed via `[pgvector]` extra |
| JAX integration | Optional | jax + jaxlib | Only installed via `[jax]` extra |
| LangGraph orchestration | Optional | langgraph package | Only installed via `[langgraph]` extra |
| Docker sandboxing | Optional | Docker daemon | `shutil.which("docker") is None`; fall back to process isolation |

### Skip marker convention

```python
import pytest
import shutil

requires_wolfram = pytest.mark.skipif(
    shutil.which("wolframscript") is None,
    reason="Wolfram Engine not installed"
)

requires_npx = pytest.mark.skipif(
    shutil.which("npx") is None,
    reason="Node.js/npx not installed"
)

requires_network = pytest.mark.skipif(
    os.getenv("OPENEINSTEIN_SKIP_NETWORK_TESTS", "0") == "1",
    reason="Network tests skipped"
)

requires_docker = pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="Docker not installed"
)

requires_latex = pytest.mark.skipif(
    shutil.which("latexmk") is None,
    reason="LaTeX not installed"
)
```

Put these in `tests/conftest.py` so every test file can import them.

### Day-1 CI green build definition

**CI passes when:** `pytest` exits 0, all non-skipped tests pass, and `pip install -e ".[dev]"` succeeds in a clean Python 3.12 environment with no special system packages.

**The arXiv MCP server** is listed as `required: true` in the example config, but for CI purposes, the arXiv *integration test* is skipped if npx is absent. The platform should handle missing optional MCP servers gracefully at runtime (log a warning, disable the tool, continue).

---

## 2. Build Environment Contract

### What the coding agent WILL have access to

| Dependency | Version | How Provided | Notes |
|-----------|---------|-------------|-------|
| Python | 3.12+ | System install | Primary language |
| pip | Latest | Comes with Python | `pip install -e ".[dev]"` |
| uv | Latest | `pip install uv` | Optional fast installer; pip is the baseline |
| pytest | ≥8.0 | `[dev]` extra | Test runner |
| mypy | ≥1.10 | `[dev]` extra | Type checking |
| ruff | ≥0.4 | `[dev]` extra | Linting + formatting |
| git | System | Pre-installed | Version control |
| SQLite | 3.x | Bundled with Python | Persistence layer |
| All `dependencies` in pyproject.toml | As specified | `pip install -e .` | NumPy, SciPy, SymPy, Pydantic, etc. |

### What the coding agent MAY have access to (configure per environment)

| Dependency | Required For | Install Method | CI Available? |
|-----------|-------------|---------------|---------------|
| Node.js 18+ / npx | arXiv MCP server | System install | Add to CI if desired; otherwise skip |
| Docker | GROBID, sandbox hardening | System install | Not in default CI |
| LaTeX (texlive + latexmk) | LaTeX publishing | System install | Not in default CI |
| Wolfram Engine | Mathematica MCP server | Wolfram installer + license | Not in CI |
| xAct | Tensor algebra in Mathematica | Mathematica package manager | Not in CI |
| Cadabra | Optional CAS | `pip install cadabra2` or system | Not in default CI |

### CI environment (GitHub Actions)

The CI workflow (`ci.yml`) should be updated to:

```yaml
name: ci

on:
  push:
    branches: ["**"]
  pull_request:

env:
  OPENEINSTEIN_SKIP_NETWORK_TESTS: "1"

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"

      - name: Lint
        run: ruff check src/ tests/

      - name: Type check
        run: mypy src/openeinstein/ --ignore-missing-imports

      - name: Run tests
        run: pytest --tb=short -q
```

### Local development environment (developer's machine)

For full integration testing locally, the developer should have:

1. Everything in CI above
2. Node.js 18+ (for arXiv MCP via npx)
3. Wolfram Engine (free for developers) + xAct (if running Mathematica tests)
4. Docker (for GROBID and hardened sandboxing)
5. LaTeX distribution (texlive-full or BasicTeX + latexmk)
6. API keys in `.env` (see §3)

---

## 3. Credentials and Secrets

### `.env` file — update `.env.example` to include all keys

```bash
# === LLM Provider Keys (at least one required) ===
ANTHROPIC_API_KEY=          # For Claude models (reasoning, generation, fast)
OPENAI_API_KEY=             # For GPT/o-series models (fallback or primary)
GOOGLE_API_KEY=             # For Gemini models (optional additional provider)

# === Wolfram / Mathematica ===
WOLFRAM_APP_ID=             # Wolfram Alpha API (optional, for quick lookups)
# Note: Wolfram Engine uses a local license, not an API key.
# Activate with: wolframscript -activate
# xAct is a free Mathematica package — no key needed, install via:
#   git clone https://github.com/xAct-contrib/xAct ~/.Mathematica/Applications/xAct

# === Literature Tool Keys ===
S2_API_KEY=                 # Semantic Scholar API (free tier available at semanticscholar.org/product/api)
ADS_API_KEY=                # NASA ADS API (free at ui.adsabs.harvard.edu/user/settings/token)
INSPIRE_API_KEY=            # INSPIRE-HEP (optional — most endpoints are keyless)
ZOTERO_API_KEY=             # Zotero Web API (from zotero.org/settings/keys)
ZOTERO_USER_ID=             # Zotero numeric user ID

# === Optional Service Keys ===
CROSSREF_MAILTO=            # CrossRef polite pool (your email, not a secret but improves rate limits)

# === Build/Test Flags ===
OPENEINSTEIN_SKIP_NETWORK_TESTS=0   # Set to 1 to skip tests requiring network
OPENEINSTEIN_LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR
```

### Key requirements by phase

| Phase | Keys Needed | Can Tests Run Without? |
|-------|------------|----------------------|
| 0 (Bootstrap) | None | Yes — no LLM calls |
| 1 (Core Framework) | None | Yes — all tests use mocks |
| 2 (Agents + Security) | None for unit tests; ANTHROPIC_API_KEY or OPENAI_API_KEY for smoke tests | Unit tests: yes. Smoke tests: need 1 key |
| 3 (CAS + Numerical) | Wolfram Engine license (local) for Mathematica tests | SymPy tests: yes. Mathematica tests: skip if absent |
| 4 (Literature) | S2_API_KEY, ADS_API_KEY for integration tests | Skipped if keys absent |
| 5 (Campaign Engine) | Same as Phase 2 | Unit tests: yes |
| 6 (CLI + Reports) | Same as Phase 2 | Yes for structure tests |
| 7 (Integration) | All keys for full E2E | Partial run possible with subset |

### What has NO key / is free

- **arXiv API**: No key needed (rate-limited by default)
- **INSPIRE-HEP REST API**: No key for most endpoints
- **CrossRef**: No key, but a `mailto` parameter gets you into the polite pool
- **SymPy**: Free, pure Python
- **Cadabra**: Free, open source
- **xAct**: Free Mathematica package
- **Wolfram Engine**: Free for developers (requires account + activation)

---

## 4. Verification Loop Contract

The implementation plan depends on the agent being able to run verification after every task. Here is exactly what must work:

### Commands the agent must be able to execute

```bash
# After every task:
pytest tests/unit/test_<component>.py          # Unit tests for the component
pytest tests/                                   # Full test suite (must not regress)
mypy src/openeinstein/<module>/                  # Type checking per module
ruff check src/ tests/                          # Lint check

# After every phase boundary:
pytest tests/integration/                       # Integration tests
pip install -e ".[dev]" && pytest               # Clean install + full suite

# For specific verification:
python -c "from openeinstein.<module> import <Class>"  # Import smoke test
openeinstein --help                              # CLI smoke test (after Phase 6)
```

### Git commit discipline

The agent commits after each task passes its acceptance criteria:

```bash
# Pattern for each task:
git add <specific files>
git commit -m "Task X.Y: <description>

- Acceptance criteria: <what was verified>
- Tests: pytest tests/unit/test_<component>.py passes
- Type check: mypy src/openeinstein/<module>/ passes"
```

### What "tests pass" means

- `pytest` exit code 0
- All non-skipped tests pass
- Skipped tests are explicitly marked with the skip markers from `conftest.py`
- No new warnings in `mypy` output (use `--ignore-missing-imports` for third-party libs without stubs)
- `ruff check` passes (auto-fixable issues can be fixed with `ruff check --fix`)

### Fresh-context validation

At plan steps 3, 4, and 6 (per the 15-step dev loop in §17.2), the agent should do a fresh-context check. In practice for an AI coding agent, this means:

1. Re-read CLAUDE.md and the relevant canonical doc
2. Re-read the task's acceptance criteria
3. Run the full test suite
4. Verify the integration contract (imports work, interfaces match)

---

## 5. Stop Conditions and Agent Kickoff Instructions

The following instructions should be included at the top of the agent's session context (in CLAUDE.md or as a system prompt prefix) when kicking off the build.

### Agent Kickoff Instructions

```markdown
# OpenEinstein Build Agent Instructions

You are executing the OpenEinstein Implementation Plan (BUILD-READY.md +
OpenEinstein-Implementation-Plan.md). Follow these rules strictly:

## Execution Order
1. Execute tasks in the order specified in §19 (Sequential Build Order).
2. Do NOT jump ahead to a later phase while earlier tasks have failing tests.
3. Within a phase, tasks marked ∥ (parallel) may be done in any order,
   but all tasks in a phase must pass before starting the next phase.

## Commit Discipline
4. Commit after each task passes its acceptance criteria.
5. Each commit message references the task ID (e.g., "Task 1.3: Implement
   persistence layer").
6. Run `pytest` before every commit. Do not commit if tests fail.
7. Run `ruff check src/ tests/` and `mypy src/openeinstein/` before
   committing. Fix issues before committing.

## Dependency Handling
8. The local development environment should have all dependencies installed
   (run scripts/setup-dev-environment.sh first). The agent should:
   a. Implement the interface/protocol fully.
   b. Write unit tests with mock/stub implementations.
   c. Write integration tests that call the REAL service/tool.
   d. Run integration tests locally — they should PASS, not skip.
   e. Integration tests also have skip markers (conftest.py) so CI stays
      green, but locally they must execute.
   f. If a dependency is genuinely missing locally, STOP and report it
      rather than silently skipping. The developer should install it.

## Testing Requirements
9. Every new module gets unit tests in tests/unit/.
10. Every cross-module interaction gets integration tests in tests/integration/.
11. Use pytest fixtures and conftest.py for shared test infrastructure.
12. Mock all external services (LLM APIs, MCP servers, network calls) in
    unit tests. Never make real API calls in unit tests.
13. Integration tests that require real services use skip markers.

## Architecture Guards
14. Never hardcode model names or provider names in business logic.
    Use logical roles ("reasoning", "generation", "fast", "embeddings").
15. Never call MCP servers or CLI tools directly from agent/campaign code.
    Route everything through ToolBus.
16. Never put physics-subfield-specific logic in core platform modules.
    That belongs in campaign-packs/.
17. All Pydantic models go at module boundaries. Use typed signatures.

## Quality Gates
18. Before starting each phase, re-read the relevant sections of
    CLAUDE.md and the implementation plan.
19. After completing each phase, run the full test suite and verify
    zero regressions.
20. If you encounter a bug in a previously-completed task while working
    on a new one, fix it immediately, add a regression test, and update
    the Living Error Log in CLAUDE.md.

## Stop Conditions — When to STOP and ask for help
21. If more than 3 consecutive test runs fail on the same issue, STOP
    and report the problem.
22. If a task's acceptance criteria are ambiguous or contradictory, STOP
    and ask for clarification.
23. If you discover that the architecture needs a fundamental change
    (not just a bug fix), STOP and propose the change before implementing.
24. If `pip install -e ".[dev]"` fails in a clean environment, STOP
    immediately — the dependency chain is broken.
25. If total test count drops (tests are being deleted rather than fixed),
    STOP and investigate.
```

### Updates to CLAUDE.md

The existing CLAUDE.md should be amended with a new section:

```markdown
## Build Execution Rules

See BUILD-READY.md for the complete pre-development readiness document, including:
- Core vs. plugin scope (what must pass CI vs. what can be skipped)
- Build environment contract (what tools are available)
- Credentials and secrets (.env structure)
- Verification loop (what commands to run after every task)
- Stop conditions (when to halt and ask for help)

The agent MUST read BUILD-READY.md before beginning any implementation work.
```

---

## 6. Summary Checklist

Before handing the repo to the coding agent, verify:

- [ ] **CLAUDE.md** updated with pointer to BUILD-READY.md
- [ ] **BUILD-READY.md** (this file) committed to repo root
- [ ] **.env.example** updated with all key placeholders (see §3 above)
- [ ] **.env** created locally with at least `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` filled in
- [ ] **ci.yml** updated to skip network tests and include lint/type-check steps
- [ ] **tests/conftest.py** created with skip markers for optional dependencies
- [ ] **Python 3.12** confirmed installed: `python3 --version`
- [ ] **pip install -e ".[dev]"** succeeds in the repo
- [ ] **pytest** runs and exits 0 (currently 0 tests, 0 failures)
- [ ] **git** initialized with clean working tree

### Optional (for full local integration testing)

- [ ] Node.js 18+ installed: `node --version`
- [ ] Wolfram Engine activated: `wolframscript -code '1+1'` returns `2`
- [ ] xAct installed: `wolframscript -code 'Needs["xAct`xTensor`"]; Print["ok"]'`
- [ ] Docker running: `docker ps`
- [ ] LaTeX installed: `latexmk --version`
- [ ] API keys populated in `.env`
