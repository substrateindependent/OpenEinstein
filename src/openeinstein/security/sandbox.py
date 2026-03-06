"""Per-run session sandbox with isolated filesystem and scoped approvals."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from openeinstein.security.core import ApprovalDecision, ApprovalsStore

_logger = logging.getLogger(__name__)

_DEFAULT_BASE = Path(".openeinstein") / "sandboxes"


class SessionSandbox:
    """Creates an isolated directory per run for artifacts, working files, and tool outputs.

    Use as a context manager to ensure cleanup on exit::

        with SessionSandbox(run_id="run-001") as sandbox:
            result_path = sandbox.resolve("artifacts/result.json")
    """

    def __init__(
        self,
        *,
        run_id: str,
        base_dir: Path | None = None,
    ) -> None:
        self._base = base_dir or _DEFAULT_BASE
        self._run_id = run_id
        self._path = self._base / run_id
        self._path.mkdir(parents=True, exist_ok=True)
        # Create standard subdirectories
        (self._path / "artifacts").mkdir(exist_ok=True)
        (self._path / "working").mkdir(exist_ok=True)
        (self._path / "tool-outputs").mkdir(exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def resolve(self, relative: str) -> Path:
        """Resolve a relative path within the sandbox boundary.

        Raises:
            SecurityError: If the resolved path escapes the sandbox.
        """
        candidate = (self._path / relative).resolve()
        sandbox_resolved = self._path.resolve()
        if not str(candidate).startswith(str(sandbox_resolved)):
            raise SecurityError(
                f"Path '{relative}' resolves outside sandbox boundary: {candidate}"
            )
        return candidate

    def cleanup(self) -> None:
        """Remove the sandbox directory tree.  Safe to call multiple times."""
        if self._path.exists():
            shutil.rmtree(self._path, ignore_errors=True)

    def __enter__(self) -> SessionSandbox:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()


class SecurityError(Exception):
    """Raised when a sandbox boundary violation is detected."""


class ScopedApprovalsStore:
    """Wraps :class:`ApprovalsStore` with per-run scoping.

    Approvals are stored with a ``{run_id}:{action}`` key so that
    grants in one run are invisible to another run's scope.
    """

    def __init__(self, base_store: ApprovalsStore, *, run_id: str) -> None:
        self._store = base_store
        self._run_id = run_id

    def _scoped_key(self, action: str) -> str:
        return f"{self._run_id}:{action}"

    def grant(self, action: str) -> ApprovalDecision:
        return self._store.grant(self._scoped_key(action))

    def revoke(self, action: str) -> ApprovalDecision:
        return self._store.revoke(self._scoped_key(action))

    def is_approved(self, action: str) -> bool:
        return self._store.is_approved(self._scoped_key(action))

    def list(self) -> list[str]:
        """Return actions approved for this run (without the run_id prefix)."""
        prefix = f"{self._run_id}:"
        return [
            a[len(prefix):]
            for a in self._store.list()
            if a.startswith(prefix)
        ]

    def reset_run(self) -> None:
        """Revoke all approvals scoped to this run."""
        for action in self.list():
            self._store.revoke(self._scoped_key(action))
