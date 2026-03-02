"""Packaging validation from wheel/sdist artifacts in a clean virtualenv."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path


def _run(command: list[str], *, cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _venv_executable(venv_root: Path, name: str) -> Path:
    bin_dir = "Scripts" if sys.platform.startswith("win") else "bin"
    return venv_root / bin_dir / name


def test_clean_venv_install_from_wheel_and_sdist(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    _run(
        [sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(dist_dir)],
        cwd=repo_root,
    )

    wheel_file = sorted(dist_dir.glob("openeinstein-*.whl"))[-1]
    sdist_file = sorted(dist_dir.glob("openeinstein-*.tar.gz"))[-1]
    with zipfile.ZipFile(wheel_file) as wheel_zip:
        members = wheel_zip.namelist()
        assert any(
            name.endswith("openeinstein/gateway/web/static/control-ui/index.html")
            for name in members
        )
    with tarfile.open(sdist_file, "r:gz") as sdist_tar:
        members = sdist_tar.getnames()
        assert any(
            name.endswith("src/openeinstein/gateway/web/static/control-ui/index.html")
            for name in members
        )

    clean_venv = tmp_path / "clean-venv"
    venv.EnvBuilder(with_pip=True, clear=True).create(clean_venv)
    pip_exe = _venv_executable(clean_venv, "pip")
    oe_exe = _venv_executable(clean_venv, "openeinstein")
    py_exe = _venv_executable(clean_venv, "python")

    # Wheel install validation.
    _run([str(pip_exe), "install", str(wheel_file)], cwd=repo_root)
    _run(
        [
            str(py_exe),
            "-c",
            (
                "from pathlib import Path; "
                "from openeinstein.gateway.web.config import DashboardConfig; "
                "static_dir = Path(DashboardConfig().static_dir); "
                "assert static_dir.exists(); "
                "assert (static_dir / 'index.html').exists(); "
                "assert 'site-packages' in str(static_dir) or 'dist-packages' in str(static_dir)"
            ),
        ],
        cwd=repo_root,
    )
    _run([str(oe_exe), "--help"], cwd=repo_root)
    _run(
        [
            str(oe_exe),
            "config",
            "--validate",
            "--path",
            str(repo_root / "configs" / "openeinstein.example.yaml"),
        ],
        cwd=repo_root,
    )
    _run([str(oe_exe), "eval", "list", "--path", str(repo_root / "evals")], cwd=repo_root)
    _run(
        [str(oe_exe), "pack", "list", "--packs-root", str(repo_root / "campaign-packs")],
        cwd=repo_root,
    )

    script_checks = [
        ("openeinstein-mcp-registry", ["--db-path", str(tmp_path / "registry.db"), "--list-tools"]),
        ("openeinstein-mcp-sympy", ["--list-tools"]),
        ("openeinstein-mcp-mathematica", ["--list-tools"]),
        ("openeinstein-mcp-cadabra", ["--list-tools"]),
        ("openeinstein-mcp-scanner", ["--list-tools"]),
        ("openeinstein-mcp-python-sandbox", ["--list-tools"]),
    ]
    for script_name, args in script_checks:
        script = _venv_executable(clean_venv, script_name)
        completed = _run([str(script), *args], cwd=repo_root)
        payload = json.loads(completed.stdout)
        assert isinstance(payload, list)
        assert payload

    # sdist install validation in the same clean venv.
    _run([str(pip_exe), "uninstall", "-y", "openeinstein"], cwd=repo_root)
    _run([str(pip_exe), "install", str(sdist_file)], cwd=repo_root)
    _run([str(oe_exe), "--help"], cwd=repo_root)
