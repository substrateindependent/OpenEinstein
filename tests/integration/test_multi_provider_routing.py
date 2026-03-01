"""Integration coverage for multi-provider routing equivalence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openeinstein.evals import EvalRunner
from openeinstein.persistence import CampaignDB
from openeinstein.routing import ModelConfig, ModelRouter, RoutingConfig


def _build_router(reasoning_provider: str, generation_provider: str) -> ModelRouter:
    payload = {
        "model_routing": {
            "roles": {
                "reasoning": {
                    "description": "reasoning provider role",
                    "default": {"provider": reasoning_provider, "model": "reasoning-v1"},
                    "fallback": {"provider": "provider-a", "model": "reasoning-fallback"},
                },
                "generation": {
                    "description": "generation provider role",
                    "default": {"provider": generation_provider, "model": "generation-v1"},
                    "fallback": {"provider": "provider-c", "model": "generation-fallback"},
                },
                "fast": {
                    "description": "fast provider role",
                    "default": {"provider": "provider-fast", "model": "fast-v1"},
                },
                "embeddings": {
                    "description": "embeddings provider role",
                    "default": {"provider": "provider-emb", "model": "emb-v1"},
                },
            }
        }
    }
    return ModelRouter(RoutingConfig.model_validate(payload))


def _normalize_reasoning(payload: dict[str, Any]) -> bool:
    if "viable" in payload:
        return bool(payload["viable"])
    if "decision" in payload:
        return payload["decision"] == "keep"
    raise ValueError(f"Unsupported reasoning payload: {payload}")


def _normalize_generation(payload: dict[str, Any]) -> bool:
    if "viable" in payload:
        return bool(payload["viable"])
    if "result" in payload:
        return payload["result"] == "positive"
    raise ValueError(f"Unsupported generation payload: {payload}")


def _reasoning_call(model: str, config: ModelConfig) -> dict[str, Any]:
    viability = model in {"general_relativity", "lambda_cdm", "horndeski_safe_slice"}
    if config.provider == "provider-a":
        return {"decision": "keep" if viability else "reject"}
    if config.provider == "provider-b":
        return {"viable": viability, "confidence": 0.93}
    raise RuntimeError(f"reasoning unavailable for {config.provider}")


def _generation_call(model: str, viable: bool, config: ModelConfig) -> dict[str, Any]:
    if config.provider == "provider-fail":
        raise RuntimeError("simulated transient provider failure")
    if config.provider == "provider-c":
        return {"result": "positive" if viable else "negative", "model": model}
    return {"viable": viable, "model": model}


def _run_suite_with_router(router: ModelRouter, db_path: Path) -> dict[str, bool]:
    db = CampaignDB(db_path)

    def executor(payload: dict[str, object]) -> dict[str, object]:
        model = str(payload["model"])
        reasoning = router.run_with_fallback("reasoning", lambda cfg: _reasoning_call(model, cfg))
        viable_hint = _normalize_reasoning(reasoning)
        generation = router.run_with_fallback(
            "generation",
            lambda cfg: _generation_call(model, viable_hint, cfg),
        )
        return {"viable": _normalize_generation(generation)}

    runner = EvalRunner(db, executor=executor)
    suite = runner.load_suite(
        Path("campaign-packs/modified-gravity-action-search/evals/known-models.yaml")
    )
    case_models = {case.name: str(case.input["model"]) for case in suite.cases}
    report = runner.run_suite(suite, run_id=f"routing-{db_path.stem}")
    assert report.failed_cases == 0
    outputs = {
        case_models[case.case_name]: bool(case.actual["viable"])
        for case in report.case_results
    }
    db.close()
    return outputs


def test_multi_provider_campaign_results_are_functionally_equivalent(tmp_path: Path) -> None:
    router_primary = _build_router("provider-a", "provider-a")
    router_secondary = _build_router("provider-b", "provider-fail")

    primary_results = _run_suite_with_router(router_primary, tmp_path / "primary.db")
    secondary_results = _run_suite_with_router(router_secondary, tmp_path / "secondary.db")

    assert secondary_results == primary_results
    assert primary_results == {
        "general_relativity": True,
        "lambda_cdm": True,
        "toy_ghost_model": False,
        "toy_tachyon_model": False,
        "horndeski_safe_slice": True,
    }
