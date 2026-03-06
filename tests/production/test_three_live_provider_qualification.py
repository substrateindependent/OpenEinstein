"""Live-provider release qualification tests (IC-PR-04)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from openeinstein.routing.provider_qualification import LiveProviderQualifier

pytestmark = pytest.mark.production


@pytest.mark.skipif(
    os.getenv("OPENEINSTEIN_ENFORCE_LIVE_PROVIDER_TESTS", "0") != "1",
    reason="Live provider gate disabled (set OPENEINSTEIN_ENFORCE_LIVE_PROVIDER_TESTS=1 to enforce)",
)
def test_three_live_providers_qualify_for_release() -> None:
    qualifier = LiveProviderQualifier.from_environment(Path("configs/openeinstein.example.yaml"))
    report = qualifier.qualify(min_providers=3)

    assert report.passed is True
    assert report.passing_provider_count >= 3
    assert "anthropic" in report.passing_providers
    assert "openai" in report.passing_providers
