#!/usr/bin/env python3
"""Audit whether the current branch and v1.12 package are ready to publish."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO = "MaciejR/large-scale-demand-forecasting-benchmark"
EXPECTED_REMOTE_URL = f"https://github.com/{REPO}.git"
EXPECTED_PUBLIC_URL = f"https://github.com/{REPO}"
BRANCH = "v1.7-tirex-m5-rohlik"
RELEASE_DIR = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair")
ZIP_PATH = Path(f"{RELEASE_DIR}.zip")


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def try_run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def audit_git(repo_root: Path) -> list[str]:
    findings: list[str] = []
    branch = run(["git", "branch", "--show-current"], repo_root)
    head = run(["git", "rev-parse", "HEAD"], repo_root)
    origin = run(["git", "rev-parse", f"origin/{BRANCH}"], repo_root)
    remote_url = run(["git", "remote", "get-url", "origin"], repo_root)
    dirty = run(["git", "status", "--porcelain", "--untracked-files=all"], repo_root)

    if branch != BRANCH:
        findings.append(f"current branch is {branch}, expected {BRANCH}")
    if head != origin:
        findings.append(f"HEAD {head} differs from origin/{BRANCH} {origin}")
    if remote_url != EXPECTED_REMOTE_URL:
        findings.append(f"origin URL is {remote_url}, expected {EXPECTED_REMOTE_URL}")
    if dirty:
        findings.append("working tree is dirty")
    return findings


def audit_release(repo_root: Path, require_complete_log: bool) -> list[str]:
    findings: list[str] = []
    release_dir = repo_root / RELEASE_DIR
    zip_path = repo_root / ZIP_PATH
    commit_path = release_dir / "COMMIT.txt"
    head = run(["git", "rev-parse", "HEAD"], repo_root)

    if not release_dir.is_dir():
        findings.append(f"missing release directory: {RELEASE_DIR}")
    if not zip_path.is_file():
        findings.append(f"missing release zip: {ZIP_PATH}")
    if not commit_path.is_file():
        findings.append(f"missing release COMMIT.txt: {RELEASE_DIR / 'COMMIT.txt'}")
    elif commit_path.read_text(encoding="utf-8").strip() != head:
        findings.append("release COMMIT.txt does not match HEAD")

    publication_log_command = ["python3", "tools/audit_publication_log_v112.py"]
    if require_complete_log:
        publication_log_command.append("--require-complete")

    for command in [
        ["python3", "tools/audit_release_privacy.py", str(RELEASE_DIR)],
        ["python3", "tools/audit_release_manifest.py", str(RELEASE_DIR)],
        ["python3", "tools/audit_release_provenance.py", str(RELEASE_DIR)],
        ["python3", "tools/audit_zenodo_metadata.py"],
        publication_log_command,
    ]:
        code, _stdout, stderr = try_run(command, repo_root)
        if code != 0:
            findings.append(f"{' '.join(command)} failed: {stderr}")

    return findings


def github_visibility(repo_root: Path) -> tuple[str | None, str | None]:
    code, stdout, stderr = try_run(
        ["gh", "repo", "view", REPO, "--json", "visibility,url"],
        repo_root,
    )
    if code != 0:
        return None, stderr or "gh repo view failed"
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return None, f"could not parse gh output: {exc}"
    url = payload.get("url")
    if url != EXPECTED_PUBLIC_URL:
        return payload.get("visibility"), f"GitHub URL is {url}, expected {EXPECTED_PUBLIC_URL}"
    return payload.get("visibility"), None


def audit_github_visibility(repo_root: Path, require_public: bool) -> list[str]:
    visibility, error = github_visibility(repo_root)
    if error:
        return [error]
    if visibility is None:
        return ["GitHub visibility could not be determined"]
    if require_public and visibility != "PUBLIC":
        return [f"GitHub repository visibility is {visibility}, expected PUBLIC"]
    return []


def audit(repo_root: Path, require_public: bool, require_complete_log: bool) -> list[str]:
    findings = audit_git(repo_root) + audit_release(repo_root, require_complete_log)
    visibility_findings = audit_github_visibility(repo_root, require_public)
    findings.extend(visibility_findings)
    if require_public:
        command = ["python3", "tools/audit_github_release.py", "--verify-download"]
        code, _stdout, stderr = try_run(command, repo_root)
        if code != 0:
            findings.append(f"{' '.join(command)} failed: {stderr}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-public",
        action="store_true",
        help="Fail unless the GitHub repository is public.",
    )
    parser.add_argument(
        "--require-complete-log",
        action="store_true",
        help="Fail unless docs/PUBLICATION_LOG_V1.12.md is complete after Zenodo publication.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    findings = audit(
        repo_root,
        require_public=args.require_public,
        require_complete_log=args.require_complete_log,
    )
    if findings:
        print("Publication readiness audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print("Publication readiness audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
