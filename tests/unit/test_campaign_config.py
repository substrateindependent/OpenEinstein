"""Unit tests for campaign config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.campaigns import CampaignConfigLoader


def test_campaign_config_loader_valid_and_invalid(tmp_path: Path) -> None:
    config_path = tmp_path / "campaign.yaml"
    config_path.write_text(
        """
campaign:
  name: test-pack
  version: "0.1.0"
  search_space:
    generator_skill: seed-skill
  gate_pipeline:
    - name: Gate A
      skill: gate-a
      cas_requirements: [symbolic_simplify]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    config = CampaignConfigLoader.load_config(config_path)
    assert config.name == "test-pack"
    assert config.gate_pipeline[0].skill == "gate-a"

    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text(
        """
campaign:
  name: broken-pack
  version: "0.1.0"
  search_space:
    generator_skill: seed
  gate_pipeline:
    - name: Missing Skill
      cas_requirements: [x]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid campaign config"):
        CampaignConfigLoader.load_config(invalid_path)


def test_campaign_config_capability_and_dependency_validation(tmp_path: Path) -> None:
    config_path = tmp_path / "campaign.yaml"
    config_path.write_text(
        """
campaign:
  name: dependency-pack
  version: "0.1.0"
  search_space:
    generator_skill: seed
  dependencies:
    tools: [registry, scanner]
  gate_pipeline:
    - name: Gate A
      skill: gate-a
      cas_requirements: [tensor_algebra]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    config = CampaignConfigLoader.load_config(config_path)

    with pytest.raises(ValueError, match="No backend satisfies gate"):
        CampaignConfigLoader.resolve_capabilities(
            config.gate_pipeline,
            {"sympy": {"symbolic_simplify"}},
        )

    with pytest.raises(ValueError, match="Missing required tool dependencies"):
        CampaignConfigLoader.validate_tool_dependencies(config, {"registry"})
