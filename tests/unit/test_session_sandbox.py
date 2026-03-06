"""Unit tests for session sandbox and scoped approvals (Story 6.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openeinstein.security.core import ApprovalsStore
from openeinstein.security.sandbox import ScopedApprovalsStore, SecurityError, SessionSandbox


class TestSessionSandbox:
    def test_creates_sandbox_directory(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        sandbox_dir = sandbox.path
        assert sandbox_dir.exists()
        assert sandbox_dir.is_dir()

    def test_sandbox_path_includes_run_id(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-042", base_dir=tmp_path)
        assert "run-042" in str(sandbox.path)

    def test_artifacts_subdir_created(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        assert (sandbox.path / "artifacts").is_dir()

    def test_working_subdir_created(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        assert (sandbox.path / "working").is_dir()

    def test_tool_outputs_subdir_created(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        assert (sandbox.path / "tool-outputs").is_dir()

    def test_resolve_path_inside_sandbox(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        resolved = sandbox.resolve("artifacts/result.json")
        assert str(resolved).startswith(str(sandbox.path))

    def test_resolve_path_outside_sandbox_raises(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        with pytest.raises(SecurityError, match="outside sandbox"):
            sandbox.resolve("../../etc/passwd")

    def test_resolve_absolute_outside_raises(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        with pytest.raises(SecurityError, match="outside sandbox"):
            sandbox.resolve("/etc/passwd")

    def test_cleanup_removes_directory(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        sandbox_path = sandbox.path
        assert sandbox_path.exists()
        sandbox.cleanup()
        assert not sandbox_path.exists()

    def test_cleanup_on_nonexistent_is_noop(self, tmp_path: Path) -> None:
        sandbox = SessionSandbox(run_id="run-001", base_dir=tmp_path)
        sandbox.cleanup()
        sandbox.cleanup()  # should not raise

    def test_context_manager(self, tmp_path: Path) -> None:
        with SessionSandbox(run_id="run-ctx", base_dir=tmp_path) as sandbox:
            sandbox_path = sandbox.path
            assert sandbox_path.exists()
        assert not sandbox_path.exists()

    def test_context_manager_cleans_on_error(self, tmp_path: Path) -> None:
        sandbox_path = None
        try:
            with SessionSandbox(run_id="run-err", base_dir=tmp_path) as sandbox:
                sandbox_path = sandbox.path
                raise RuntimeError("intentional")
        except RuntimeError:
            pass
        assert sandbox_path is not None
        assert not sandbox_path.exists()


class TestScopedApprovalsStore:
    def test_grant_scoped_to_run_id(self, tmp_path: Path) -> None:
        store_path = tmp_path / "approvals.json"
        base_store = ApprovalsStore(store_path)
        scoped = ScopedApprovalsStore(base_store, run_id="run-A")
        scoped.grant("action_x")
        assert scoped.is_approved("action_x")

    def test_scoped_isolation(self, tmp_path: Path) -> None:
        """Approvals in one run don't leak to another."""
        store_path = tmp_path / "approvals.json"
        base_store = ApprovalsStore(store_path)
        scoped_a = ScopedApprovalsStore(base_store, run_id="run-A")
        scoped_b = ScopedApprovalsStore(base_store, run_id="run-B")

        scoped_a.grant("action_x")
        assert scoped_a.is_approved("action_x")
        assert not scoped_b.is_approved("action_x")

    def test_list_returns_only_scoped(self, tmp_path: Path) -> None:
        store_path = tmp_path / "approvals.json"
        base_store = ApprovalsStore(store_path)
        scoped_a = ScopedApprovalsStore(base_store, run_id="run-A")
        scoped_b = ScopedApprovalsStore(base_store, run_id="run-B")

        scoped_a.grant("alpha")
        scoped_b.grant("beta")

        assert "alpha" in scoped_a.list()
        assert "beta" not in scoped_a.list()
        assert "beta" in scoped_b.list()
        assert "alpha" not in scoped_b.list()

    def test_revoke_scoped(self, tmp_path: Path) -> None:
        store_path = tmp_path / "approvals.json"
        base_store = ApprovalsStore(store_path)
        scoped = ScopedApprovalsStore(base_store, run_id="run-A")
        scoped.grant("action_x")
        scoped.revoke("action_x")
        assert not scoped.is_approved("action_x")

    def test_reset_run_clears_only_that_run(self, tmp_path: Path) -> None:
        store_path = tmp_path / "approvals.json"
        base_store = ApprovalsStore(store_path)
        scoped_a = ScopedApprovalsStore(base_store, run_id="run-A")
        scoped_b = ScopedApprovalsStore(base_store, run_id="run-B")

        scoped_a.grant("alpha")
        scoped_b.grant("beta")

        scoped_a.reset_run()
        assert not scoped_a.is_approved("alpha")
        assert scoped_b.is_approved("beta")

    def test_grant_returns_decision(self, tmp_path: Path) -> None:
        store_path = tmp_path / "approvals.json"
        base_store = ApprovalsStore(store_path)
        scoped = ScopedApprovalsStore(base_store, run_id="run-A")
        decision = scoped.grant("action_y")
        assert decision.action == "run-A:action_y"
        assert decision.approved is True

    def test_revoke_on_nonexistent_is_noop(self, tmp_path: Path) -> None:
        store_path = tmp_path / "approvals.json"
        base_store = ApprovalsStore(store_path)
        scoped = ScopedApprovalsStore(base_store, run_id="run-A")
        scoped.revoke("never_granted")  # should not raise


class TestImports:
    def test_session_sandbox_importable(self) -> None:
        from openeinstein.security.sandbox import SessionSandbox as SS

        assert SS is not None

    def test_scoped_approvals_importable_from_security(self) -> None:
        from openeinstein.security import ScopedApprovalsStore as SAS

        assert SAS is not None
