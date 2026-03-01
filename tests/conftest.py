"""Shared test fixtures and skip markers for OpenEinstein tests.

Import skip markers in test files:
    from conftest import requires_wolfram, requires_network, ...

Or use directly as decorators:
    @pytest.mark.skipif(...)
"""

import importlib.util
import os
import shutil
from pathlib import Path

import pytest


def _load_repo_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


_load_repo_env()

# ---------------------------------------------------------------------------
# Skip markers for optional system dependencies
# ---------------------------------------------------------------------------

requires_wolfram = pytest.mark.skipif(
    shutil.which("wolframscript") is None,
    reason="Wolfram Engine not installed",
)

requires_npx = pytest.mark.skipif(
    shutil.which("npx") is None,
    reason="Node.js / npx not installed",
)

requires_docker = pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="Docker not installed",
)

requires_latex = pytest.mark.skipif(
    shutil.which("latexmk") is None,
    reason="LaTeX (latexmk) not installed",
)

requires_cadabra = pytest.mark.skipif(
    importlib.util.find_spec("cadabra2") is None and shutil.which("cadabra2") is None,
    reason="cadabra2 runtime not installed",
)

# ---------------------------------------------------------------------------
# Skip markers for network-dependent tests
# ---------------------------------------------------------------------------

requires_network = pytest.mark.skipif(
    os.getenv("OPENEINSTEIN_SKIP_NETWORK_TESTS", "0") == "1",
    reason="Network tests skipped (OPENEINSTEIN_SKIP_NETWORK_TESTS=1)",
)

# ---------------------------------------------------------------------------
# Skip markers for API keys
# ---------------------------------------------------------------------------

requires_s2_key = pytest.mark.skipif(
    not os.getenv("S2_API_KEY"),
    reason="S2_API_KEY not set",
)

requires_ads_key = pytest.mark.skipif(
    not os.getenv("ADS_API_KEY"),
    reason="ADS_API_KEY not set",
)

requires_zotero_key = pytest.mark.skipif(
    not os.getenv("ZOTERO_API_KEY"),
    reason="ZOTERO_API_KEY not set",
)

requires_anthropic_key = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

requires_openai_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)

requires_any_llm_key = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="No LLM API key set (need ANTHROPIC_API_KEY or OPENAI_API_KEY)",
)
