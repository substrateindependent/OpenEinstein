"""Ed25519 pack signing and verification (Story 4.1).

Uses the ``cryptography`` library for Ed25519 keypair generation,
signing, and verification of campaign pack integrity.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

_SIGNATURE_FILENAME = "pack.sig"


class PackSigner:
    """Ed25519 signing and verification for campaign packs."""

    @staticmethod
    def generate_keypair() -> tuple[bytes, bytes]:
        """Generate an Ed25519 keypair.

        Returns (public_key_bytes, private_key_bytes) in raw format.
        """
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        private_bytes = private_key.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        )
        return public_bytes, private_bytes

    @staticmethod
    def sign_pack(pack_path: Path, private_key_bytes: bytes) -> Path:
        """Sign a pack directory with Ed25519.

        Computes SHA-256 of all pack files (sorted, excluding pack.sig)
        and signs the digest. Returns path to the signature file.
        """
        private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        digest = _compute_pack_digest(pack_path)
        signature = private_key.sign(digest)

        sig_path = pack_path / _SIGNATURE_FILENAME
        sig_path.write_bytes(signature)
        return sig_path

    @staticmethod
    def verify_pack(
        pack_path: Path,
        public_key_bytes: bytes,
        signature_path: Path,
    ) -> bool:
        """Verify a pack's Ed25519 signature.

        Returns True if valid, False if invalid or signature missing.
        """
        if not signature_path.exists():
            return False

        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            digest = _compute_pack_digest(pack_path)
            signature = signature_path.read_bytes()
            public_key.verify(signature, digest)
            return True
        except Exception:
            return False


def _compute_pack_digest(pack_path: Path) -> bytes:
    """Compute SHA-256 digest of all files in a pack (sorted, excluding pack.sig)."""
    hasher = hashlib.sha256()
    files = sorted(
        f for f in pack_path.rglob("*")
        if f.is_file() and f.name != _SIGNATURE_FILENAME
    )
    for file_path in files:
        # Include relative path in hash for path-sensitivity
        rel = file_path.relative_to(pack_path).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(file_path.read_bytes())
    return hasher.digest()
