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
SANDBOX_TOKEN_ENV_VARS = ("ZENODO_SANDBOX_ACCESS_TOKEN", "ZENODO_SANDBOX_TOKEN")
PLACEHOLDER_TOKENS = {"...", "<token>", "<your-token>", "changeme", "todo", "token"}
KNOWN_TOKEN_ENV_VARS = TOKEN_ENV_VARS + SANDBOX_TOKEN_ENV_VARS


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


def load_local_env_tokens(
    repo_root: Path,
    environ: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return env plus known Zenodo token variables from a local .env file."""

    merged = dict(os.environ if environ is None else environ)
    env_path = repo_root / ".env"
    if not env_path.is_file():
        return merged

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in KNOWN_TOKEN_ENV_VARS or merged.get(key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        merged[key] = value
    return merged


def audit_token(
    require_token: bool,
    environ: dict[str, str] | None = None,
    token_env_vars: tuple[str, ...] = TOKEN_ENV_VARS,
) -> list[str]:
    if not require_token:
        return []

    environ = os.environ if environ is None else environ
    values = {name: environ.get(name, "").strip() for name in token_env_vars}
    present = {name: value for name, value in values.items() if value}
    valid = {
        name: value
        for name, value in present.items()
        if value.lower() not in PLACEHOLDER_TOKENS
    }
    if valid:
        return []
    names = " or ".join(token_env_vars)
    if present:
        present_names = ", ".join(sorted(present))
        return [f"Zenodo API token environment variable is a placeholder ({present_names})"]
    return [f"missing Zenodo API token environment variable ({names})"]


def audit(
    repo_root: Path,
    require_token: bool,
    token_env_vars: tuple[str, ...] = TOKEN_ENV_VARS,
) -> list[str]:
    findings = audit_git_state(repo_root)
    findings.extend(audit_package_files(repo_root))
    findings.extend(audit_zenodo_metadata.audit(repo_root))
    findings.extend(audit_github_release.audit(repo_root))
    token_environ = load_local_env_tokens(repo_root)
    findings.extend(
        audit_token(require_token, environ=token_environ, token_env_vars=token_env_vars)
    )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-token",
        action="store_true",
        help="Fail unless ZENODO_ACCESS_TOKEN or ZENODO_TOKEN is set.",
    )
    parser.add_argument(
        "--sandbox-token",
        action="store_true",
        help="Check ZENODO_SANDBOX_ACCESS_TOKEN or ZENODO_SANDBOX_TOKEN instead.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    token_env_vars = SANDBOX_TOKEN_ENV_VARS if args.sandbox_token else TOKEN_ENV_VARS
    findings = audit(repo_root, require_token=args.require_token, token_env_vars=token_env_vars)
    if findings:
        print("Zenodo upload readiness audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    token_status = (
        "token present"
        if audit_token(
            True,
            environ=load_local_env_tokens(repo_root),
            token_env_vars=token_env_vars,
        )
        == []
        else "token not checked"
    )
    print(f"Zenodo upload readiness audit passed ({token_status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
