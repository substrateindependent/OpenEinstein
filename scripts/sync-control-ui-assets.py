#!/usr/bin/env python3
"""Copy built dashboard assets into the Python package static directory."""

from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / "dist" / "control-ui"
    destination = repo_root / "src" / "openeinstein" / "gateway" / "web" / "static" / "control-ui"

    if not source.exists():
        raise SystemExit(f"Missing build output: {source}. Run `pnpm --dir ui build` first.")

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)
    print(f"Synced UI assets to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
