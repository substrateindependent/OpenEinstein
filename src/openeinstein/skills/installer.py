"""Pack installer with hash pinning and security scanning."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from openeinstein.security.core import MetadataPinStore, ScanFinding, SecurityScanner
from openeinstein.skills.models import PackManifest


class InstallResult(BaseModel):
    """Result of a pack installation."""

    success: bool
    pack_name: str
    error: str = ""
    findings: list[ScanFinding] = Field(default_factory=list)
    hash: str = ""
    signature_verified: bool | None = None


class PackInstaller:
    """Installs campaign packs with hash pinning and security scanning."""

    def __init__(
        self,
        managed_root: str | Path = Path(".openeinstein") / "managed-packs",
        pins_path: str | Path = Path(".openeinstein") / "metadata-pins.json",
        trusted_public_key: bytes | None = None,
    ) -> None:
        self._managed_root = Path(managed_root)
        self._pin_store = MetadataPinStore(pins_path)
        self._scanner = SecurityScanner()
        self._trusted_public_key = trusted_public_key

    def install(self, source_path: str | Path, *, verify: bool = True) -> InstallResult:
        """Install a pack from source_path to the managed directory.

        Args:
            source_path: Path to the pack directory.
            verify: If True, verify hash against existing pin (if any).

        Returns:
            InstallResult with success status, findings, and hash.
        """
        source = Path(source_path)
        pack_name = source.name

        # Validate manifest exists
        manifest_path = source / "manifest.json"
        if not manifest_path.exists():
            return InstallResult(
                success=False,
                pack_name=pack_name,
                error=f"Missing manifest.json in pack '{pack_name}'",
            )

        # Load and validate manifest
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            PackManifest.model_validate(manifest_data)
        except Exception as exc:
            return InstallResult(
                success=False,
                pack_name=pack_name,
                error=f"Invalid manifest in pack '{pack_name}': {exc}",
            )

        # Compute hash of pack contents
        pack_hash = self._compute_pack_hash(source)

        # Verify against existing pin if verify=True
        if verify:
            existing_pins = self._pin_store._read()
            if pack_name in existing_pins and existing_pins[pack_name] != pack_hash:
                return InstallResult(
                    success=False,
                    pack_name=pack_name,
                    error=f"Integrity mismatch for pack '{pack_name}': "
                    f"computed hash does not match pinned hash",
                    hash=pack_hash,
                )

        # Run security scanner
        findings = self._scanner.scan_paths([source])

        # Verify Ed25519 signature if trusted key is configured and signature exists
        sig_verified: bool | None = None
        sig_path = source / "pack.sig"
        if self._trusted_public_key is not None and sig_path.exists():
            from openeinstein.security.signing import PackSigner

            sig_verified = PackSigner.verify_pack(
                source, self._trusted_public_key, sig_path,
            )
            if not sig_verified:
                return InstallResult(
                    success=False,
                    pack_name=pack_name,
                    error=f"Signature verification failed for pack '{pack_name}'",
                    findings=findings,
                    hash=pack_hash,
                    signature_verified=False,
                )

        # Copy pack to managed directory
        dest = self._managed_root / pack_name
        if dest.exists():
            shutil.rmtree(dest)
        self._managed_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)

        # Pin the hash
        self._pin_store.pin(pack_name, pack_hash)

        return InstallResult(
            success=True,
            pack_name=pack_name,
            findings=findings,
            hash=pack_hash,
            signature_verified=sig_verified,
        )

    @staticmethod
    def _compute_pack_hash(pack_path: Path) -> str:
        """Compute SHA-256 over all pack files in sorted order."""
        hasher = hashlib.sha256()
        files = sorted(
            p for p in pack_path.rglob("*") if p.is_file()
        )
        for file_path in files:
            # Include relative path in hash for structural integrity
            rel = file_path.relative_to(pack_path)
            hasher.update(str(rel).encode("utf-8"))
            hasher.update(file_path.read_bytes())
        return hasher.hexdigest()
