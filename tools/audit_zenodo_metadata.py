#!/usr/bin/env python3
"""Audit the v1.12 Zenodo metadata draft against the current release package."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


METADATA_PATH = Path("docs/ZENODO_METADATA_V1.12.json")
ROOT_METADATA_PATH = Path(".zenodo.json")
ZIP_PATH = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip")
RELEASE_DIR = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair")
ASSET_NAME = "zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip"
VERSION = "v1.12-timesfm-fev-bench-wape-covariance-repair"
GITHUB_REPO_URL = "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark"
GITHUB_RELEASE_URL = f"{GITHUB_REPO_URL}/releases/tag/v1.12"
HISTORICAL_DOI = "10.5281/zenodo.21338004"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_metadata(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def related_identifier_map(metadata: dict) -> dict[tuple[str, str], dict]:
    result = {}
    for item in metadata.get("related_identifiers", []):
        result[(item.get("identifier"), item.get("relation"))] = item
    return result


def audit_metadata(metadata: dict) -> list[str]:
    findings: list[str] = []

    expected = {
        "upload_type": "publication",
        "publication_type": "technicalnote",
        "publication_date": "2026-07-20",
        "version": VERSION,
        "language": "eng",
        "access_right": "open",
        "license": "cc-by-4.0",
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            findings.append(f"{key}={metadata.get(key)!r}, expected {value!r}")

    title = metadata.get("title", "")
    for required in ["v1.12", "TimesFM", "fev-bench", "WAPE"]:
        if required not in title:
            findings.append(f"title missing {required!r}")

    creators = metadata.get("creators", [])
    if not creators or creators[0].get("name") != "Rubczynski, Maciej":
        findings.append("first creator must be Rubczynski, Maciej")

    keywords = set(metadata.get("keywords", []))
    for keyword in ["demand forecasting", "foundation models", "TimesFM", "reproducibility"]:
        if keyword not in keywords:
            findings.append(f"missing keyword: {keyword}")

    related = related_identifier_map(metadata)
    required_related = {
        (GITHUB_REPO_URL, "isSupplementTo"),
        (GITHUB_RELEASE_URL, "isIdenticalTo"),
        (HISTORICAL_DOI, "isNewVersionOf"),
    }
    for key in required_related:
        if key not in related:
            findings.append(f"missing related identifier: {key[0]} ({key[1]})")
    for item in metadata.get("related_identifiers", []):
        if (
            item.get("identifier") == HISTORICAL_DOI
            and item.get("relation") != "isNewVersionOf"
        ):
            findings.append(
                "historical v1.0 DOI must only appear as isNewVersionOf in v1.12 metadata"
            )

    notes = metadata.get("notes", "")
    for required in [ASSET_NAME, "COMMIT.txt", "CHECKSUMS.txt"]:
        if required not in notes:
            findings.append(f"notes missing {required!r}")

    return findings


def audit(repo_root: Path) -> list[str]:
    metadata_path = repo_root / METADATA_PATH
    root_metadata_path = repo_root / ROOT_METADATA_PATH
    zip_path = repo_root / ZIP_PATH
    commit_path = repo_root / RELEASE_DIR / "COMMIT.txt"

    findings: list[str] = []
    if not metadata_path.is_file():
        return [f"missing metadata file: {METADATA_PATH}"]
    if not root_metadata_path.is_file():
        findings.append(f"missing root metadata file: {ROOT_METADATA_PATH}")
    if not zip_path.is_file():
        return [f"missing release zip: {ZIP_PATH}"]
    if not commit_path.is_file():
        findings.append(f"missing release COMMIT.txt: {RELEASE_DIR / 'COMMIT.txt'}")

    metadata = load_metadata(metadata_path)
    if root_metadata_path.is_file():
        root_metadata = load_metadata(root_metadata_path)
        if root_metadata != metadata:
            findings.append(f"{ROOT_METADATA_PATH} does not match {METADATA_PATH}")
    # Do not require the outer zip checksum in this metadata file: the metadata
    # is itself packaged inside the zip, so embedding that hash would be
    # circular.  Package hashes are audited through CHECKSUMS.txt and the GitHub
    # release asset digest instead.
    sha256(zip_path)
    findings.extend(audit_metadata(metadata))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    findings = audit(repo_root)
    if findings:
        print("Zenodo metadata audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print(f"Zenodo metadata audit passed for {METADATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
