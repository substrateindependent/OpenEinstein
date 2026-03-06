"""Integration tests for CLI pack/skill commands (Story 2.4)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from openeinstein.cli.main import app

runner = CliRunner()


# ── Helper to create a minimal pack ──


def _create_pack(
    root: Path,
    name: str = "test-pack",
    *,
    version: str = "1.0.0",
    include_campaign_yaml: bool = True,
) -> Path:
    """Create a minimal pack with manifest.json and SKILL.md."""
    pack_dir = root / name
    pack_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": name,
        "version": version,
        "author": "Test Author",
        "license": "MIT",
        "sha256": "placeholder",
    }
    (pack_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (pack_dir / "SKILL.md").write_text(
        f"---\nversion: {version}\n---\n# {name}\nA test skill.\n",
        encoding="utf-8",
    )

    if include_campaign_yaml:
        (pack_dir / "campaign.yaml").write_text(
            f"name: {name}\nversion: {version}\n", encoding="utf-8"
        )

    return pack_dir


# ── pack install --skip-verify ──


def test_pack_install_with_skip_verify(tmp_path: Path, monkeypatch: object) -> None:
    """pack install --skip-verify installs a pack via PackInstaller."""
    source = _create_pack(tmp_path / "source")
    managed = tmp_path / "managed"
    pins = tmp_path / "pins.json"

    # monkeypatch to use tmp managed/pins paths
    import openeinstein.cli.main as cli_mod

    monkeypatch.setattr(cli_mod, "_managed_packs_root", lambda: managed)  # type: ignore[attr-defined]
    monkeypatch.setattr(cli_mod, "_pins_path", lambda: pins)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["pack", "install", str(source), "--skip-verify"])
    assert result.exit_code == 0
    assert "Installed" in result.output or "installed" in result.output.lower()


def test_pack_install_invalid_source(tmp_path: Path) -> None:
    """pack install with non-existent path gives error."""
    result = runner.invoke(app, ["pack", "install", str(tmp_path / "nope")])
    assert result.exit_code != 0


def test_pack_install_without_manifest(tmp_path: Path, monkeypatch: object) -> None:
    """pack install without manifest.json fails descriptively."""
    pack_dir = tmp_path / "source" / "no-manifest"
    pack_dir.mkdir(parents=True)
    (pack_dir / "SKILL.md").write_text("# NoManifest\nMissing.\n", encoding="utf-8")
    (pack_dir / "campaign.yaml").write_text("name: no-manifest\n", encoding="utf-8")

    managed = tmp_path / "managed"
    pins = tmp_path / "pins.json"

    import openeinstein.cli.main as cli_mod

    monkeypatch.setattr(cli_mod, "_managed_packs_root", lambda: managed)  # type: ignore[attr-defined]
    monkeypatch.setattr(cli_mod, "_pins_path", lambda: pins)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["pack", "install", str(pack_dir), "--skip-verify"])
    assert result.exit_code != 0 or "manifest" in result.output.lower()


# ── pack verify ──


def test_pack_verify_pinned_passes(tmp_path: Path, monkeypatch: object) -> None:
    """pack verify on a pinned pack reports PASS."""
    source = _create_pack(tmp_path / "source")
    managed = tmp_path / "managed"
    pins = tmp_path / "pins.json"

    import openeinstein.cli.main as cli_mod

    monkeypatch.setattr(cli_mod, "_managed_packs_root", lambda: managed)  # type: ignore[attr-defined]
    monkeypatch.setattr(cli_mod, "_pins_path", lambda: pins)  # type: ignore[attr-defined]

    # First install to pin
    runner.invoke(app, ["pack", "install", str(source), "--skip-verify"])

    # Now verify the installed pack
    installed = managed / "test-pack"
    result = runner.invoke(app, ["pack", "verify", str(installed)])
    assert result.exit_code == 0
    assert "pass" in result.output.lower() or "verified" in result.output.lower()


def test_pack_verify_unpinned_reports_not_pinned(tmp_path: Path, monkeypatch: object) -> None:
    """pack verify on an unpinned pack gives clear 'not pinned' message."""
    source = _create_pack(tmp_path / "source")
    pins = tmp_path / "pins.json"

    import openeinstein.cli.main as cli_mod

    monkeypatch.setattr(cli_mod, "_pins_path", lambda: pins)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["pack", "verify", str(source)])
    assert "not pinned" in result.output.lower() or "no pin" in result.output.lower()


def test_pack_verify_tampered_fails(tmp_path: Path, monkeypatch: object) -> None:
    """pack verify detects tampered pack after install."""
    source = _create_pack(tmp_path / "source")
    managed = tmp_path / "managed"
    pins = tmp_path / "pins.json"

    import openeinstein.cli.main as cli_mod

    monkeypatch.setattr(cli_mod, "_managed_packs_root", lambda: managed)  # type: ignore[attr-defined]
    monkeypatch.setattr(cli_mod, "_pins_path", lambda: pins)  # type: ignore[attr-defined]

    # Install first
    runner.invoke(app, ["pack", "install", str(source), "--skip-verify"])

    # Tamper with installed pack
    installed = managed / "test-pack"
    (installed / "SKILL.md").write_text("# Tampered\nEvil.\n", encoding="utf-8")

    result = runner.invoke(app, ["pack", "verify", str(installed)])
    assert result.exit_code != 0 or "fail" in result.output.lower() or "mismatch" in result.output.lower()


# ── pack pin ──


def test_pack_pin_creates_pin(tmp_path: Path, monkeypatch: object) -> None:
    """pack pin manually pins a pack's hash."""
    source = _create_pack(tmp_path / "source")
    pins = tmp_path / "pins.json"

    import openeinstein.cli.main as cli_mod

    monkeypatch.setattr(cli_mod, "_pins_path", lambda: pins)  # type: ignore[attr-defined]

    result = runner.invoke(app, ["pack", "pin", str(source)])
    assert result.exit_code == 0
    assert "pinned" in result.output.lower()

    # Verify pin actually exists
    pin_data = json.loads(pins.read_text(encoding="utf-8"))
    assert "test-pack" in pin_data


# ── skill list --precedence ──


def test_skill_list_precedence_shows_source_and_version(tmp_path: Path, monkeypatch: object) -> None:
    """skill list --precedence shows source and version columns."""
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nversion: 2.0.0\n---\n# My Skill\nDoes things.\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app, ["skill", "list", "--precedence", "--skills-root", str(skills_root)]
    )
    assert result.exit_code == 0
    assert "my-skill" in result.output
    assert "2.0.0" in result.output


def test_skill_list_precedence_no_skills(tmp_path: Path) -> None:
    """skill list --precedence with no skills shows empty message."""
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    result = runner.invoke(
        app, ["skill", "list", "--precedence", "--skills-root", str(empty_root)]
    )
    assert result.exit_code == 0
    assert "no skill" in result.output.lower() or result.output.strip() == ""


def test_skill_list_precedence_shows_bundled_source(tmp_path: Path) -> None:
    """skill list --precedence shows source label (bundled/managed/workspace)."""
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "research"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Research\nDoes research.\n", encoding="utf-8")

    result = runner.invoke(
        app, ["skill", "list", "--precedence", "--skills-root", str(skills_root)]
    )
    assert result.exit_code == 0
    assert "research" in result.output
    # Source should appear in output
    assert "bundled" in result.output.lower() or "workspace" in result.output.lower() or "managed" in result.output.lower()
