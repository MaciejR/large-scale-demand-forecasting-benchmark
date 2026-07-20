#!/usr/bin/env python3
"""Audit the public GitHub v1.12 release tag and uploaded zip asset."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = "MaciejR/large-scale-demand-forecasting-benchmark"
TAG = "v1.12"
RELEASE_DIR = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair")
ZIP_PATH = Path(f"{RELEASE_DIR}.zip")
ASSET_NAME = "zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip"
RELEASE_URL = f"https://github.com/{REPO}/releases/tag/{TAG}"


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def release_payload(repo_root: Path) -> dict:
    stdout = run(
        [
            "gh",
            "release",
            "view",
            TAG,
            "--repo",
            REPO,
            "--json",
            "tagName,name,url,targetCommitish,assets,isDraft,isPrerelease",
        ],
        repo_root,
    )
    return json.loads(stdout)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_release_asset(repo_root: Path, output_dir: Path) -> Path:
    run(
        [
            "gh",
            "release",
            "download",
            TAG,
            "--repo",
            REPO,
            "--pattern",
            ASSET_NAME,
            "--dir",
            str(output_dir),
        ],
        repo_root,
    )
    return output_dir / ASSET_NAME


def audit_downloaded_asset(downloaded_path: Path, local_zip_path: Path) -> list[str]:
    findings: list[str] = []
    if not downloaded_path.is_file():
        return [f"downloaded release asset missing: {downloaded_path}"]
    if not local_zip_path.is_file():
        return [f"missing local zip: {local_zip_path}"]
    downloaded_sha = sha256(downloaded_path)
    local_sha = sha256(local_zip_path)
    if downloaded_sha != local_sha:
        findings.append(
            f"downloaded asset SHA-256 {downloaded_sha} does not match local zip {local_sha}"
        )
    return findings


def find_asset(payload: dict, name: str) -> dict | None:
    for asset in payload.get("assets", []):
        if asset.get("name") == name:
            return asset
    return None


def matching_assets(payload: dict, name: str) -> list[dict]:
    return [asset for asset in payload.get("assets", []) if asset.get("name") == name]


def audit_payload(payload: dict, expected_commit: str, zip_path: Path) -> list[str]:
    findings: list[str] = []

    if payload.get("tagName") != TAG:
        findings.append(f"release tag is {payload.get('tagName')}, expected {TAG}")
    if payload.get("url") != RELEASE_URL:
        findings.append(f"release URL is {payload.get('url')}, expected {RELEASE_URL}")
    if payload.get("targetCommitish") != expected_commit:
        findings.append(
            f"release target is {payload.get('targetCommitish')}, expected {expected_commit}"
        )
    if payload.get("isDraft"):
        findings.append("release is still a draft")
    if payload.get("isPrerelease"):
        findings.append("release is marked prerelease")

    assets = matching_assets(payload, ASSET_NAME)
    if not assets:
        findings.append(f"missing release asset: {ASSET_NAME}")
        return findings
    if len(assets) != 1:
        findings.append(f"release has {len(assets)} assets named {ASSET_NAME}, expected 1")
    asset = assets[0]

    local_size = zip_path.stat().st_size if zip_path.is_file() else None
    if local_size is None:
        findings.append(f"missing local zip: {zip_path}")
    elif asset.get("size") != local_size:
        findings.append(f"asset size is {asset.get('size')}, expected {local_size}")

    if zip_path.is_file():
        local_digest = sha256(zip_path)
        expected_digest = f"sha256:{local_digest}"
        if asset.get("digest") != expected_digest:
            findings.append(f"asset digest is {asset.get('digest')}, expected {expected_digest}")

    expected_url = f"https://github.com/{REPO}/releases/download/{TAG}/{ASSET_NAME}"
    if asset.get("url") != expected_url:
        findings.append(f"asset URL is {asset.get('url')}, expected {expected_url}")
    if asset.get("state") != "uploaded":
        findings.append(f"asset state is {asset.get('state')}, expected uploaded")

    return findings


def audit(repo_root: Path, verify_download: bool = False) -> list[str]:
    commit_path = repo_root / RELEASE_DIR / "COMMIT.txt"
    zip_path = repo_root / ZIP_PATH
    if not commit_path.is_file():
        return [f"missing release COMMIT.txt: {RELEASE_DIR / 'COMMIT.txt'}"]
    expected_commit = commit_path.read_text(encoding="utf-8").strip()
    payload = release_payload(repo_root)
    findings = audit_payload(payload, expected_commit, zip_path)
    if verify_download and not findings:
        with tempfile.TemporaryDirectory(prefix="v112-github-release-") as tmp:
            downloaded_path = download_release_asset(repo_root, Path(tmp))
            findings.extend(audit_downloaded_asset(downloaded_path, zip_path))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-download",
        action="store_true",
        help="Download the release asset and compare its SHA-256 to the local zip.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    findings = audit(repo_root, verify_download=args.verify_download)
    if findings:
        print("GitHub release audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print(f"GitHub release audit passed for {RELEASE_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
