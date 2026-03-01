"""Unit tests for skill registry behavior."""

from __future__ import annotations

from pathlib import Path

from openeinstein.skills import SkillRegistry


def _write_skill(root: Path, name: str, body: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def test_skill_discovery_and_instruction_loading(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", "# Alpha\nAlpha description\n")
    _write_skill(tmp_path, "beta", "# Beta\nBeta description\n")
    registry = SkillRegistry([tmp_path])

    discovered = registry.discover_skills()
    assert sorted(discovered.keys()) == ["alpha", "beta"]
    instructions = registry.load_instructions("alpha")
    assert instructions.name == "alpha"
    assert "Alpha description" in instructions.text


def test_skill_context_budget_and_progressive_disclosure(tmp_path: Path) -> None:
    _write_skill(tmp_path, "short", "# Short\nsmall\n")
    _write_skill(tmp_path, "long", "# Long\n" + ("x" * 200))
    registry = SkillRegistry([tmp_path], max_chars_per_file=40, max_total_chars=80)

    bundle = registry.build_context(["short", "long", "missing"])
    assert "Skill: short" in bundle.content
    assert any("missing" in omitted for omitted in bundle.report.omitted_files)
    assert bundle.report.truncated_files or any(
        "long/SKILL.md" in omitted for omitted in bundle.report.omitted_files
    )
    assert bundle.report.total_chars <= 80
