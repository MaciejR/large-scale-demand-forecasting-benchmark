#!/usr/bin/env python3
"""Audit whether the v1.12 package is ready for a Zenodo upload step."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import audit_github_release
import audit_zenodo_metadata


REPO = "MaciejR/large-scale-demand-forecasting-benchmark"
BRANCH = "v1.7-tirex-m5-rohlik"
RELEASE_DIR = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair")
ZIP_PATH = Path(f"{RELEASE_DIR}.zip")
TOKEN_ENV_VARS = ("ZENODO_ACCESS_TOKEN", "ZENODO_TOKEN")


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def audit_git_state(repo_root: Path) -> list[str]:
    findings: list[str] = []
    head = run(["git", "rev-parse", "HEAD"], repo_root)
    origin = run(["git", "rev-parse", f"origin/{BRANCH}"], repo_root)
    dirty = run(["git", "status", "--porcelain", "--untracked-files=all"], repo_root)

    commit_path = repo_root / RELEASE_DIR / "COMMIT.txt"
    if not commit_path.is_file():
        findings.append(f"missing release COMMIT.txt: {RELEASE_DIR / 'COMMIT.txt'}")
    elif commit_path.read_text(encoding="utf-8").strip() != head:
        findings.append("release COMMIT.txt does not match HEAD")

    if head != origin:
        findings.append(f"HEAD {head} differs from origin/{BRANCH} {origin}")
    if dirty:
        findings.append("working tree is dirty")
    return findings


def audit_package_files(repo_root: Path) -> list[str]:
    findings: list[str] = []
    zip_path = repo_root / ZIP_PATH
    release_dir = repo_root / RELEASE_DIR
    metadata_path = repo_root / audit_zenodo_metadata.METADATA_PATH

    if not release_dir.is_dir():
        findings.append(f"missing release directory: {RELEASE_DIR}")
    if not zip_path.is_file():
        findings.append(f"missing release zip: {ZIP_PATH}")
    elif zip_path.stat().st_size <= 0:
        findings.append(f"release zip is empty: {ZIP_PATH}")
    if not metadata_path.is_file():
        findings.append(f"missing Zenodo metadata draft: {audit_zenodo_metadata.METADATA_PATH}")
    return findings


def audit_token(require_token: bool, environ: dict[str, str] | None = None) -> list[str]:
    if not require_token:
        return []

    environ = os.environ if environ is None else environ
    if any(environ.get(name, "").strip() for name in TOKEN_ENV_VARS):
        return []
    names = " or ".join(TOKEN_ENV_VARS)
    return [f"missing Zenodo API token environment variable ({names})"]


def audit(repo_root: Path, require_token: bool) -> list[str]:
    findings = audit_git_state(repo_root)
    findings.extend(audit_package_files(repo_root))
    findings.extend(audit_zenodo_metadata.audit(repo_root))
    findings.extend(audit_github_release.audit(repo_root))
    findings.extend(audit_token(require_token))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-token",
        action="store_true",
        help="Fail unless ZENODO_ACCESS_TOKEN or ZENODO_TOKEN is set.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    findings = audit(repo_root, require_token=args.require_token)
    if findings:
        print("Zenodo upload readiness audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    token_status = "token present" if audit_token(True) == [] else "token not checked"
    print(f"Zenodo upload readiness audit passed ({token_status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
