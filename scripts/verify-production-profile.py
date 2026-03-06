#!/usr/bin/env python3
"""Enforce production-profile test policy for OpenEinstein cutover."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    python = repo_root / ".venv" / "bin" / "python"
    pytest_cmd = [str(python), "-m", "pytest", "tests/production", "-ra", "-q"]

    completed = subprocess.run(
        pytest_cmd,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)

    if completed.returncode != 0:
        print("\n[production-profile] FAIL: tests/production returned non-zero status.")
        return completed.returncode

    skipped_lines = [line.strip() for line in stdout.splitlines() if line.startswith("SKIPPED")]
    xfailed = bool(re.search(r"\bxfailed\b", stdout, flags=re.IGNORECASE))
    xpassed = bool(re.search(r"\bxpassed\b", stdout, flags=re.IGNORECASE))

    enforce_live = os.getenv("OPENEINSTEIN_ENFORCE_LIVE_PROVIDER_TESTS", "0") == "1"
    allowed_skip_patterns: list[str] = []
    if not enforce_live:
        allowed_skip_patterns.append("Live provider gate disabled")

    unexpected_skips: list[str] = []
    for line in skipped_lines:
        if any(pattern in line for pattern in allowed_skip_patterns):
            continue
        unexpected_skips.append(line)

    if xfailed or xpassed:
        print("\n[production-profile] FAIL: xfail/xpass is not allowed in production profile.")
        return 2

    if unexpected_skips:
        print("\n[production-profile] FAIL: unexpected skipped tests detected:")
        for line in unexpected_skips:
            print(f"- {line}")
        return 3

    if enforce_live and any("Live provider gate disabled" in line for line in skipped_lines):
        print(
            "\n[production-profile] FAIL: live-provider qualification was skipped while enforcement is enabled."
        )
        return 4

    print("\n[production-profile] PASS: production profile policy satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
