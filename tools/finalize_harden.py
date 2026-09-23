#!/usr/bin/env python3
"""Write Tiny Tapeout provenance files after an isolated LibreLane run."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from source_manifest import manifest, matches_build


def git_output(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(cwd), *args], text=True, stderr=subprocess.DEVNULL
    ).strip()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def public_repo_url(remote: str | None) -> str | None:
    """Publish only a credential-free public GitHub repository URL."""
    if remote is None:
        return None
    remote = re.sub(r'^git@github\.com:', 'https://github.com/', remote)
    remote = re.sub(r'^ssh://git@github\.com/', 'https://github.com/', remote)
    url = urlsplit(remote)
    if (url.scheme != 'https' or url.netloc != 'github.com'
            or url.query or url.fragment
            or not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', url.path)):
        raise ValueError('Origin must be a credential-free GitHub repository URL before packaging')
    return remote.removesuffix('.git')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--pdk-version", required=True)
    args = parser.parse_args()

    root = args.project_root.resolve()
    run_dir = root / "runs" / "wokwi"
    resolved = json.loads((run_dir / "resolved.json").read_text())
    tt_commit = git_output(root / "tt", "rev-parse", "--short=8", "HEAD")

    try:
        repo = git_output(root, "remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        repo = None
    repo = public_repo_url(repo)

    try:
        commit = git_output(root, "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        commit = None
    # Never label an old layout with hashes from newer source files.
    hashes = json.loads((run_dir / "source_manifest.json").read_text())
    current = manifest(root)
    if not matches_build(root, hashes):
        raise SystemExit("Physical build inputs changed: rerun make gds before packaging")

    write_json(
        run_dir / "final" / "commit_id.json",
        {
            "app": f"Tiny Tapeout main {tt_commit}",
            "repo": repo,
            "commit": commit,
            "workflow_url": None,
            "local_build": True,
            "git_dirty": bool(git_output(root, "status", "--porcelain")),
            "source_sha256": hashes,
            "packaged_source_sha256": current,
            "metadata_update": (
                json.loads((root / 'docs/verification/metadata-update.json').read_text())
                if current != hashes else None
            ),
        },
    )
    write_json(
        run_dir / "pdk.json",
        {
            "FLOW_NAME": "LibreLane",
            "FLOW_VERSION": resolved["meta"]["librelane_version"],
            "PDK": resolved["PDK"],
            "PDK_SOURCE": "open_pdks",
            "PDK_VERSION": args.pdk_version,
        },
    )


if __name__ == "__main__":
    main()
