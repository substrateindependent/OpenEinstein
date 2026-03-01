"""Unit tests for modified-gravity campaign pack completeness."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]


def test_modified_gravity_pack_assets_present() -> None:
    root = Path("campaign-packs/modified-gravity-action-search")
    assert (root / "campaign.yaml").exists()
    assert (root / "literature-seed.yaml").exists()
    assert (root / "evals" / "known-models.yaml").exists()

    skill_paths = sorted((root / "skills").rglob("SKILL.md"))
    assert len(skill_paths) >= 5
    for skill_path in skill_paths:
        text = skill_path.read_text(encoding="utf-8")
        assert "Purpose:" in text

    template_paths = sorted((root / "templates").rglob("*.yaml"))
    assert {path.stem for path in template_paths} >= {
        "cosmology-reduction",
        "perturbation-analysis",
        "stability-analysis",
    }

    eval_payload = yaml.safe_load((root / "evals" / "known-models.yaml").read_text(encoding="utf-8"))
    assert eval_payload["eval_suite"]["cases"]
