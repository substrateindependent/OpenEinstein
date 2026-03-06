"""Integration tests for precedence-aware skill discovery (Story 2.2)."""

from __future__ import annotations

from pathlib import Path

from openeinstein.skills.models import SkillSource
from openeinstein.skills.registry import SkillRegistry


def test_conflicting_skills_workspace_wins(tmp_path: Path) -> None:
    """Integration: conflicting skills in workspace and bundled roots — workspace wins."""
    bundled = tmp_path / "bundled"
    managed = tmp_path / "managed"
    workspace = tmp_path / "workspace"

    # Create same skill in all three roots with different descriptions
    for root, desc in [(bundled, "Bundled version"), (managed, "Managed version"), (workspace, "Workspace version")]:
        skill_dir = root / "conflict-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nversion: 1.0.0\n---\n# Conflict Skill\n{desc}.\n",
            encoding="utf-8",
        )

    registry = SkillRegistry(
        roots=[bundled, managed, workspace],
        source_map={
            str(bundled): SkillSource.bundled,
            str(managed): SkillSource.managed,
            str(workspace): SkillSource.workspace,
        },
    )

    result = registry.list_with_precedence()
    assert "conflict-skill" in result
    assert result["conflict-skill"].source == SkillSource.workspace
    # Verify the winning skill's description comes from workspace
    assert "Workspace version" in result["conflict-skill"].description


def test_three_way_conflict_all_sources(tmp_path: Path) -> None:
    """Three-way conflict: workspace > managed > bundled."""
    bundled = tmp_path / "b"
    managed = tmp_path / "m"
    workspace = tmp_path / "w"

    for root, version in [(bundled, "1.0.0"), (managed, "1.1.0"), (workspace, "2.0.0")]:
        skill_dir = root / "versioned-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nversion: {version}\n---\n# Versioned Skill\nv{version} from {root.name}.\n",
            encoding="utf-8",
        )

    registry = SkillRegistry(
        roots=[bundled, managed, workspace],
        source_map={
            str(bundled): SkillSource.bundled,
            str(managed): SkillSource.managed,
            str(workspace): SkillSource.workspace,
        },
    )

    result = registry.list_with_precedence()
    winner = result["versioned-skill"]
    assert winner.source == SkillSource.workspace
    assert winner.version == "2.0.0"


def test_non_conflicting_skills_all_present(tmp_path: Path) -> None:
    """Non-conflicting skills from different roots all appear."""
    bundled = tmp_path / "bundled"
    workspace = tmp_path / "workspace"

    (bundled / "bundled-only").mkdir(parents=True)
    (bundled / "bundled-only" / "SKILL.md").write_text(
        "# Bundled Only\nOnly in bundled.\n", encoding="utf-8"
    )

    (workspace / "ws-only").mkdir(parents=True)
    (workspace / "ws-only" / "SKILL.md").write_text(
        "# WS Only\nOnly in workspace.\n", encoding="utf-8"
    )

    registry = SkillRegistry(
        roots=[bundled, workspace],
        source_map={
            str(bundled): SkillSource.bundled,
            str(workspace): SkillSource.workspace,
        },
    )

    result = registry.list_with_precedence()
    assert "bundled-only" in result
    assert result["bundled-only"].source == SkillSource.bundled
    assert "ws-only" in result
    assert result["ws-only"].source == SkillSource.workspace
