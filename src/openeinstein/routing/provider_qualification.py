"""Live provider qualification helpers for production release gating."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from openeinstein.routing.router import load_routing_config


class ProviderProbeResult(BaseModel):
    provider: str
    passed: bool
    detail: str


class ProviderQualificationReport(BaseModel):
    passed: bool
    min_required: int
    passing_provider_count: int
    passing_providers: list[str] = Field(default_factory=list)
    results: list[ProviderProbeResult] = Field(default_factory=list)


class LiveProviderQualifier:
    """Validates configured providers using key presence and optional live probes."""

    def __init__(self, providers: list[str]) -> None:
        self._providers = sorted(set(provider.lower() for provider in providers if provider))

    @classmethod
    def from_environment(cls, routing_config_path: str | Path) -> "LiveProviderQualifier":
        config = load_routing_config(routing_config_path)
        providers: list[str] = []
        roles = config.model_routing.roles
        for role_name in ("reasoning", "generation", "fast", "embeddings"):
            role = getattr(roles, role_name)
            providers.append(role.default.provider)
            for fallback in role.fallback_chain():
                providers.append(fallback.provider)
        return cls(providers)

    def qualify(self, min_providers: int = 3) -> ProviderQualificationReport:
        results = [self._probe_provider(provider) for provider in self._providers]
        passing = sorted([result.provider for result in results if result.passed])
        return ProviderQualificationReport(
            passed=len(passing) >= min_providers,
            min_required=min_providers,
            passing_provider_count=len(passing),
            passing_providers=passing,
            results=results,
        )

    def _probe_provider(self, provider: str) -> ProviderProbeResult:
        provider_lower = provider.lower()
        env_key = _provider_key(provider_lower)
        if env_key is not None and not os.getenv(env_key):
            return ProviderProbeResult(
                provider=provider_lower,
                passed=False,
                detail=f"missing key: {env_key}",
            )

        if os.getenv("OPENEINSTEIN_PROVIDER_LIVE_PROBE", "0") != "1":
            if env_key is not None:
                return ProviderProbeResult(
                    provider=provider_lower,
                    passed=True,
                    detail=f"key present: {env_key}",
                )
            return ProviderProbeResult(
                provider=provider_lower,
                passed=True,
                detail="no-key provider assumed ready (live probe disabled)",
            )

        probe = _live_probe(provider_lower)
        return ProviderProbeResult(
            provider=provider_lower,
            passed=probe["passed"],
            detail=str(probe["detail"]),
        )



def _provider_key(provider: str) -> str | None:
    mapping = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    if provider in mapping:
        return mapping[provider]
    if provider in {"local", "ollama", "fallback"}:
        return None
    return f"{provider.upper()}_API_KEY"


def _live_probe(provider: str) -> dict[str, Any]:
    try:
        if provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY", "")
            request = Request(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                },
            )
            with urlopen(request, timeout=10) as response:
                return {"passed": response.status == 200, "detail": f"status={response.status}"}

        if provider == "openai":
            key = os.getenv("OPENAI_API_KEY", "")
            request = Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            with urlopen(request, timeout=10) as response:
                return {"passed": response.status == 200, "detail": f"status={response.status}"}

        if provider in {"google", "gemini"}:
            key = os.getenv("GOOGLE_API_KEY", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            request = Request(url)
            with urlopen(request, timeout=10) as response:
                return {"passed": response.status == 200, "detail": f"status={response.status}"}

        if provider == "ollama":
            request = Request("http://127.0.0.1:11434/api/tags")
            with urlopen(request, timeout=5) as response:
                return {"passed": response.status == 200, "detail": f"status={response.status}"}

        return {"passed": False, "detail": "live probe not implemented for provider"}
    except (HTTPError, URLError, TimeoutError) as exc:
        return {"passed": False, "detail": str(exc)}
