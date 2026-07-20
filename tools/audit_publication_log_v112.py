#!/usr/bin/env python3
"""Audit the v1.12 publication log structure and completion state."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


LOG_PATH = Path("docs/PUBLICATION_LOG_V1.12.md")
RELEASE_DIR = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair")
ZIP_PATH = Path(f"{RELEASE_DIR}.zip")
ASSET_NAME = "zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip"
GITHUB_RELEASE_URL = (
    "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.12"
)
DOI_RE = re.compile(r"10\.5281/zenodo\.[0-9]+")


def audit_log_text(text: str) -> list[str]:
    findings: list[str] = []
    required_values = {
        "GitHub release URL": GITHUB_RELEASE_URL,
        "asset name": ASSET_NAME,
    }
    for label, value in required_values.items():
        if value not in text:
            findings.append(f"publication log missing {label}: {value}")
    for label in [
        "Target commit:",
        "Asset SHA-256:",
        "Production deposition ID:",
        "Production record URL:",
        "Production DOI:",
        "DOI metadata update commit:",
        "Final package SHA-256 after DOI update:",
        "Final GitHub release target after DOI update:",
    ]:
        if label not in text:
            findings.append(f"publication log missing field: {label}")
    return findings


def audit_complete_log_text(text: str) -> list[str]:
    findings: list[str] = []
    if "TODO" in text:
        findings.append("publication log still contains TODO placeholders")
    if not DOI_RE.search(text):
        findings.append("publication log does not contain a Zenodo DOI")
    if "https://doi.org/10.5281/zenodo." not in text:
        findings.append("publication log does not contain a production DOI URL")
    if "https://zenodo.org/records/" not in text:
        findings.append("publication log does not contain a production record URL")
    return findings


def audit(repo_root: Path, require_complete: bool) -> list[str]:
    log_path = repo_root / LOG_PATH
    zip_path = repo_root / ZIP_PATH
    commit_path = repo_root / RELEASE_DIR / "COMMIT.txt"
    findings: list[str] = []

    if not log_path.is_file():
        return [f"missing publication log: {LOG_PATH}"]
    if not zip_path.is_file():
        return [f"missing release zip: {ZIP_PATH}"]
    if not commit_path.is_file():
        return [f"missing release COMMIT.txt: {RELEASE_DIR / 'COMMIT.txt'}"]

    text = log_path.read_text(encoding="utf-8")
    findings.extend(audit_log_text(text))
    if require_complete:
        findings.extend(audit_complete_log_text(text))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail if post-Zenodo publication fields are still placeholders.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    findings = audit(repo_root, require_complete=args.require_complete)
    if findings:
        print("Publication log audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    suffix = "complete" if args.require_complete else "template"
    print(f"Publication log audit passed for {LOG_PATH} ({suffix})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
