#!/usr/bin/env python3
"""Prepare a private, pinned upstream checkout and local LKH build. Never vendors upstream code."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vrptw.neurolkh_baseline import UPSTREAM_COMMIT, UPSTREAM_URL, asset_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.exists():
        root.mkdir(parents=True)
        for command in (
            ["git", "init"],
            ["git", "remote", "add", "origin", UPSTREAM_URL],
            ["git", "fetch", "--depth", "1", "origin", UPSTREAM_COMMIT],
            ["git", "checkout", "--detach", "FETCH_HEAD"],
        ):
            subprocess.run(command, cwd=root, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    changed = subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=root, text=True).strip()
    if commit != UPSTREAM_COMMIT or changed:
        parser.error(
            "Existing checkout is modified or not at the pinned commit; use a new root, never reset user files"
        )
    if (root / "assets.json").exists():
        parser.error("Build manifest exists; use a new root for a new build")
    (root / "SRC/OBJ").mkdir(exist_ok=True)
    command = ["make", "-B", "-C", "SRC", "-j2"]
    with (root / "build.stdout.log").open("w") as stdout, (root / "build.stderr.log").open("w") as stderr:
        subprocess.run(command, cwd=root, stdout=stdout, stderr=stderr, check=True)
    compiler = subprocess.check_output(["cc", "--version"], text=True)
    manifest = {
        "identity": asset_identity(root),
        "build": {
            "command": command,
            "compiler": compiler,
            "created_utc": datetime.now(UTC).isoformat(),
            "scope": "Unmodified source, local research preparation; no upstream redistribution permission inferred",
        },
    }
    with (root / "assets.json").open("x") as stream:
        json.dump(manifest, stream, indent=2)
    print(json.dumps({key: value for key, value in manifest["identity"].items() if key != "source_files"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
