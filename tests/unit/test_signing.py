"""Unit tests for Ed25519 pack signing & verification (Story 4.1)."""

from __future__ import annotations

import json
from pathlib import Path

from openeinstein.security.signing import PackSigner


# ── Key generation ──


def test_generate_keypair() -> None:
    """generate_keypair returns a public/private key pair."""
    public_key, private_key = PackSigner.generate_keypair()
    assert public_key is not None
    assert private_key is not None
    assert len(public_key) > 0
    assert len(private_key) > 0


def test_keypair_are_bytes() -> None:
    """Keys are returned as bytes."""
    public_key, private_key = PackSigner.generate_keypair()
    assert isinstance(public_key, bytes)
    assert isinstance(private_key, bytes)


# ── Sign and verify round-trip ──


def test_sign_and_verify_round_trip(tmp_path: Path) -> None:
    """Sign a pack and verify — full round-trip."""
    pack_dir = _create_test_pack(tmp_path / "test-pack")

    public_key, private_key = PackSigner.generate_keypair()
    sig_path = PackSigner.sign_pack(pack_dir, private_key)
    assert sig_path.exists()

    result = PackSigner.verify_pack(pack_dir, public_key, sig_path)
    assert result is True


def test_tampered_pack_fails_verification(tmp_path: Path) -> None:
    """Tampered pack (modified file after signing) fails verification."""
    pack_dir = _create_test_pack(tmp_path / "test-pack")

    public_key, private_key = PackSigner.generate_keypair()
    sig_path = PackSigner.sign_pack(pack_dir, private_key)

    # Tamper with a file
    (pack_dir / "SKILL.md").write_text("# Tampered\nEvil content.\n", encoding="utf-8")

    result = PackSigner.verify_pack(pack_dir, public_key, sig_path)
    assert result is False


def test_wrong_public_key_fails_verification(tmp_path: Path) -> None:
    """Wrong public key fails verification."""
    pack_dir = _create_test_pack(tmp_path / "test-pack")

    _, private_key = PackSigner.generate_keypair()
    sig_path = PackSigner.sign_pack(pack_dir, private_key)

    # Use a different keypair's public key
    wrong_public_key, _ = PackSigner.generate_keypair()

    result = PackSigner.verify_pack(pack_dir, wrong_public_key, sig_path)
    assert result is False


def test_missing_signature_file_returns_false(tmp_path: Path) -> None:
    """Missing signature file returns False (not exception)."""
    pack_dir = _create_test_pack(tmp_path / "test-pack")
    public_key, _ = PackSigner.generate_keypair()

    result = PackSigner.verify_pack(pack_dir, public_key, tmp_path / "nonexistent.sig")
    assert result is False


def test_signature_file_location(tmp_path: Path) -> None:
    """Signature file is created inside the pack directory."""
    pack_dir = _create_test_pack(tmp_path / "test-pack")
    _, private_key = PackSigner.generate_keypair()

    sig_path = PackSigner.sign_pack(pack_dir, private_key)
    assert sig_path.parent == pack_dir
    assert sig_path.name == "pack.sig"


def test_sign_empty_pack_directory(tmp_path: Path) -> None:
    """Signing a directory with no signable files still works."""
    empty_dir = tmp_path / "empty-pack"
    empty_dir.mkdir()

    public_key, private_key = PackSigner.generate_keypair()
    sig_path = PackSigner.sign_pack(empty_dir, private_key)
    assert sig_path.exists()

    result = PackSigner.verify_pack(empty_dir, public_key, sig_path)
    assert result is True


def test_verify_excludes_signature_file(tmp_path: Path) -> None:
    """The signature file itself is excluded from hash computation."""
    pack_dir = _create_test_pack(tmp_path / "test-pack")

    public_key, private_key = PackSigner.generate_keypair()
    # Sign twice — second sign should produce same hash (sig excluded)
    sig_path_1 = PackSigner.sign_pack(pack_dir, private_key)
    sig_path_2 = PackSigner.sign_pack(pack_dir, private_key)

    # Both should verify
    assert PackSigner.verify_pack(pack_dir, public_key, sig_path_1)
    assert PackSigner.verify_pack(pack_dir, public_key, sig_path_2)


# ── Import smoke test ──


def test_import_pack_signer_from_security() -> None:
    from openeinstein.security import PackSigner as _PS  # noqa: F401


# ── Helper ──


def _create_test_pack(path: Path) -> Path:
    """Create a minimal test pack."""
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test-pack",
        "version": "1.0.0",
        "author": "Test",
        "license": "MIT",
        "sha256": "placeholder",
    }
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (path / "SKILL.md").write_text("# Test Pack\nA skill.\n", encoding="utf-8")
    (path / "campaign.yaml").write_text("name: test-pack\n", encoding="utf-8")
    return path
