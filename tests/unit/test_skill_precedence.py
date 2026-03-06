"""Unit tests for precedence-aware skill discovery (Story 2.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.skills.models import PackManifest, SkillMetadata, SkillSource


# ── SkillSource enum ──


def test_skill_source_bundled_exists() -> None:
    assert SkillSource.bundled.value == "bundled"


def test_skill_source_managed_exists() -> None:
    assert SkillSource.managed.value == "managed"


def test_skill_source_workspace_exists() -> None:
    assert SkillSource.workspace.value == "workspace"


def test_skill_source_precedence_rank_ordering() -> None:
    """Workspace has highest precedence, bundled has lowest."""
    assert SkillSource.workspace.precedence_rank > SkillSource.managed.precedence_rank
    assert SkillSource.managed.precedence_rank > SkillSource.bundled.precedence_rank


def test_skill_source_precedence_rank_values() -> None:
    assert SkillSource.bundled.precedence_rank == 0
    assert SkillSource.managed.precedence_rank == 1
    assert SkillSource.workspace.precedence_rank == 2


# ── SkillMetadata version & source fields ──


def test_skill_metadata_version_default_none() -> None:
    meta = SkillMetadata(name="test", description="test", path="/tmp/skill")
    assert meta.version is None


def test_skill_metadata_version_accepts_string() -> None:
    meta = SkillMetadata(name="test", description="test", path="/tmp/skill", version="1.2.3")
    assert meta.version == "1.2.3"


def test_skill_metadata_source_default_bundled() -> None:
    meta = SkillMetadata(name="test", description="test", path="/tmp/skill")
    assert meta.source == SkillSource.bundled


def test_skill_metadata_source_accepts_value() -> None:
    meta = SkillMetadata(
        name="test", description="test", path="/tmp/skill", source=SkillSource.workspace
    )
    assert meta.source == SkillSource.workspace


# ── PackManifest model ──


def test_pack_manifest_required_fields() -> None:
    manifest = PackManifest(
        name="test-pack",
        version="1.0.0",
        author="Test Author",
        license="MIT",
        sha256="abc123def456",
    )
    assert manifest.name == "test-pack"
    assert manifest.version == "1.0.0"
    assert manifest.author == "Test Author"
    assert manifest.license == "MIT"
    assert manifest.sha256 == "abc123def456"


def test_pack_manifest_optional_fields_defaults() -> None:
    manifest = PackManifest(
        name="test-pack",
        version="1.0.0",
        author="Test Author",
        license="MIT",
        sha256="abc123",
    )
    assert manifest.description is None
    assert manifest.dependencies == []
    assert manifest.min_platform_version is None
    assert manifest.tags == []


def test_pack_manifest_optional_fields_populated() -> None:
    manifest = PackManifest(
        name="test-pack",
        version="1.0.0",
        author="Test Author",
        license="MIT",
        sha256="abc123",
        description="A test pack",
        dependencies=["dep-a", "dep-b"],
        min_platform_version="0.5.0",
        tags=["physics", "gravity"],
    )
    assert manifest.description == "A test pack"
    assert manifest.dependencies == ["dep-a", "dep-b"]
    assert manifest.min_platform_version == "0.5.0"
    assert manifest.tags == ["physics", "gravity"]


def test_pack_manifest_missing_required_field_raises() -> None:
    with pytest.raises(Exception):  # noqa: B017
        PackManifest(name="test-pack", version="1.0.0")  # type: ignore[call-arg]


# ── Version extraction from YAML frontmatter ──


def test_discover_extracts_version_from_frontmatter(tmp_path: Path) -> None:
    from openeinstein.skills.registry import SkillRegistry

    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nversion: 2.1.0\n---\n# My Skill\nDoes things.\n",
        encoding="utf-8",
    )

    registry = SkillRegistry(roots=[tmp_path])
    skills = registry.discover_skills()
    assert "my-skill" in skills
    assert skills["my-skill"].version == "2.1.0"


def test_discover_no_frontmatter_version_is_none(tmp_path: Path) -> None:
    from openeinstein.skills.registry import SkillRegistry

    skill_dir = tmp_path / "simple-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Simple Skill\nNo frontmatter.\n", encoding="utf-8")

    registry = SkillRegistry(roots=[tmp_path])
    skills = registry.discover_skills()
    assert "simple-skill" in skills
    assert skills["simple-skill"].version is None


def test_discover_frontmatter_without_version_is_none(tmp_path: Path) -> None:
    from openeinstein.skills.registry import SkillRegistry

    skill_dir = tmp_path / "meta-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nauthor: someone\n---\n# Meta Skill\nHas frontmatter but no version.\n",
        encoding="utf-8",
    )

    registry = SkillRegistry(roots=[tmp_path])
    skills = registry.discover_skills()
    assert "meta-skill" in skills
    assert skills["meta-skill"].version is None


# ── SkillSource tagging in discover_skills ──


def test_discover_tags_bundled_source(tmp_path: Path) -> None:
    from openeinstein.skills.registry import SkillRegistry

    bundled_root = tmp_path / "bundled"
    skill_dir = bundled_root / "skill-a"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill A\nBundled skill.\n", encoding="utf-8")

    registry = SkillRegistry(
        roots=[bundled_root],
        source_map={str(bundled_root): SkillSource.bundled},
    )
    skills = registry.discover_skills()
    assert skills["skill-a"].source == SkillSource.bundled


def test_discover_tags_workspace_source(tmp_path: Path) -> None:
    from openeinstein.skills.registry import SkillRegistry

    ws_root = tmp_path / "workspace"
    skill_dir = ws_root / "skill-b"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill B\nWorkspace skill.\n", encoding="utf-8")

    registry = SkillRegistry(
        roots=[ws_root],
        source_map={str(ws_root): SkillSource.workspace},
    )
    skills = registry.discover_skills()
    assert skills["skill-b"].source == SkillSource.workspace


def test_discover_default_source_is_bundled(tmp_path: Path) -> None:
    """When no source_map provided, default source is bundled."""
    from openeinstein.skills.registry import SkillRegistry

    skill_dir = tmp_path / "skill-c"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill C\nDefault source.\n", encoding="utf-8")

    registry = SkillRegistry(roots=[tmp_path])
    skills = registry.discover_skills()
    assert skills["skill-c"].source == SkillSource.bundled


# ── list_with_precedence ──


def test_list_with_precedence_workspace_wins(tmp_path: Path) -> None:
    """Workspace version wins over bundled for same skill name."""
    from openeinstein.skills.registry import SkillRegistry

    bundled = tmp_path / "bundled"
    workspace = tmp_path / "workspace"

    for root in [bundled, workspace]:
        skill_dir = root / "overlap-skill"
        skill_dir.mkdir(parents=True)
        source_label = root.name
        (skill_dir / "SKILL.md").write_text(
            f"# Overlap Skill\nFrom {source_label}.\n", encoding="utf-8"
        )

    registry = SkillRegistry(
        roots=[bundled, workspace],
        source_map={
            str(bundled): SkillSource.bundled,
            str(workspace): SkillSource.workspace,
        },
    )
    result = registry.list_with_precedence()
    assert "overlap-skill" in result
    assert result["overlap-skill"].source == SkillSource.workspace


def test_list_with_precedence_managed_wins_over_bundled(tmp_path: Path) -> None:
    from openeinstein.skills.registry import SkillRegistry

    bundled = tmp_path / "bundled"
    managed = tmp_path / "managed"

    for root in [bundled, managed]:
        skill_dir = root / "shared-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"# Shared Skill\nFrom {root.name}.\n", encoding="utf-8"
        )

    registry = SkillRegistry(
        roots=[bundled, managed],
        source_map={
            str(bundled): SkillSource.bundled,
            str(managed): SkillSource.managed,
        },
    )
    result = registry.list_with_precedence()
    assert result["shared-skill"].source == SkillSource.managed


def test_list_with_precedence_unique_skills_all_present(tmp_path: Path) -> None:
    from openeinstein.skills.registry import SkillRegistry

    bundled = tmp_path / "bundled"
    workspace = tmp_path / "workspace"

    (bundled / "skill-a").mkdir(parents=True)
    (bundled / "skill-a" / "SKILL.md").write_text("# Skill A\nBundled.\n", encoding="utf-8")

    (workspace / "skill-b").mkdir(parents=True)
    (workspace / "skill-b" / "SKILL.md").write_text("# Skill B\nWorkspace.\n", encoding="utf-8")

    registry = SkillRegistry(
        roots=[bundled, workspace],
        source_map={
            str(bundled): SkillSource.bundled,
            str(workspace): SkillSource.workspace,
        },
    )
    result = registry.list_with_precedence()
    assert "skill-a" in result
    assert "skill-b" in result


def test_list_with_precedence_single_source(tmp_path: Path) -> None:
    """Precedence resolution with single source still works."""
    from openeinstein.skills.registry import SkillRegistry

    root = tmp_path / "only-root"
    (root / "solo-skill").mkdir(parents=True)
    (root / "solo-skill" / "SKILL.md").write_text("# Solo\nAlone.\n", encoding="utf-8")

    registry = SkillRegistry(roots=[root])
    result = registry.list_with_precedence()
    assert "solo-skill" in result
    assert result["solo-skill"].source == SkillSource.bundled


def test_list_with_precedence_empty_roots(tmp_path: Path) -> None:
    from openeinstein.skills.registry import SkillRegistry

    registry = SkillRegistry(roots=[tmp_path / "nonexistent"])
    result = registry.list_with_precedence()
    assert result == {}


# ── Import smoke tests ──


def test_import_skill_source_from_skills() -> None:
    from openeinstein.skills import SkillSource as _SkillSource  # noqa: F401


def test_import_pack_manifest_from_skills() -> None:
    from openeinstein.skills import PackManifest as _PackManifest  # noqa: F401
