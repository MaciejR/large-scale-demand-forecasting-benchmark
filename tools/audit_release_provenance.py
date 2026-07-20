#!/usr/bin/env python3
"""Audit version, package naming, and commit provenance for the v1.12 release."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


VERSION = "v1.12"
RELEASE_DATE = "2026-07-20"
RELEASE_STEM = "zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair"
RELEASE_DIR = Path("release") / RELEASE_STEM
ZIP_PATH = Path("release") / f"{RELEASE_STEM}.zip"
PDF_NAME = "demand-forecasting-timesfm-fev-bench-wape-covariance-repair-v1.12.pdf"
REPO_URL = "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def current_git_head(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def require_contains(text: str, needle: str, label: str, findings: list[str]) -> None:
    if needle not in text:
        findings.append(f"{label}: missing {needle!r}")


def require_regex(text: str, pattern: str, label: str, findings: list[str]) -> None:
    if not re.search(pattern, text, re.MULTILINE):
        findings.append(f"{label}: missing pattern {pattern!r}")


def display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def audit_static_files(repo_root: Path) -> list[str]:
    findings: list[str] = []

    citation = read(repo_root / "CITATION.cff")
    readme = read(repo_root / "README.md")
    release_notes = read(repo_root / "docs" / "RELEASE_V1.12.md")
    zenodo_metadata = read(repo_root / "docs" / "ZENODO_METADATA_V1.12.json")
    reproducing = read(repo_root / "REPRODUCING.md")
    build_script = read(repo_root / "tools" / "build_v112_release.sh")
    manifest_audit = read(repo_root / "tools" / "audit_release_manifest.py")
    privacy_audit = read(repo_root / "tools" / "audit_release_privacy.py")
    main_tex = read(repo_root / "paper" / "latex" / "main.tex")

    require_regex(citation, rf'^version:\s*"{re.escape(VERSION)}"$', "CITATION.cff", findings)
    require_regex(citation, rf'^date-released:\s*"{re.escape(RELEASE_DATE)}"$', "CITATION.cff", findings)
    require_contains(citation, REPO_URL, "CITATION.cff", findings)

    for label, text in [
        ("README.md", readme),
        ("docs/RELEASE_V1.12.md", release_notes),
        ("REPRODUCING.md", reproducing),
    ]:
        require_contains(text, str(ZIP_PATH), label, findings)

    for label, text in [
        ("docs/RELEASE_V1.12.md", release_notes),
        ("tools/build_v112_release.sh", build_script),
        ("tools/audit_release_manifest.py", manifest_audit),
    ]:
        require_contains(text, PDF_NAME, label, findings)

    for label, text in [
        ("tools/build_v112_release.sh", build_script),
        ("tools/audit_release_manifest.py", manifest_audit),
        ("tools/audit_release_privacy.py", privacy_audit),
        ("tools/audit_release_provenance.py", read(repo_root / "tools" / "audit_release_provenance.py")),
    ]:
        require_contains(text, RELEASE_STEM, label, findings)

    require_contains(main_tex, REPO_URL, "paper/latex/main.tex", findings)
    require_contains(main_tex, "COMMIT.txt", "paper/latex/main.tex", findings)
    require_contains(main_tex, "CHECKSUMS.txt", "paper/latex/main.tex", findings)
    require_contains(zenodo_metadata, str(ZIP_PATH.name), "docs/ZENODO_METADATA_V1.12.json", findings)
    require_contains(zenodo_metadata, REPO_URL, "docs/ZENODO_METADATA_V1.12.json", findings)

    return findings


def audit_release_dir(repo_root: Path, release_dir: Path, expected_head: str) -> list[str]:
    findings: list[str] = []
    commit_path = release_dir / "COMMIT.txt"
    zip_path = Path(f"{release_dir}.zip")
    pdf_path = release_dir / "manuscript" / PDF_NAME
    package_readme = release_dir / "README.md"
    replication_release_notes = release_dir / "replication" / "docs" / "RELEASE_V1.12.md"

    if not release_dir.is_dir():
        return [f"release directory does not exist: {release_dir}"]
    if not zip_path.is_file():
        findings.append(f"missing release zip: {zip_path}")
    if not pdf_path.is_file():
        findings.append(f"missing manuscript PDF: {display_path(pdf_path, repo_root)}")
    if not commit_path.is_file():
        findings.append(f"missing COMMIT.txt: {display_path(commit_path, repo_root)}")
    else:
        package_sha = commit_path.read_text(encoding="utf-8").strip()
        if package_sha != expected_head:
            findings.append(f"COMMIT.txt={package_sha}, expected HEAD={expected_head}")

    for path in [package_readme, replication_release_notes]:
        if not path.is_file():
            findings.append(f"missing release note file: {display_path(path, repo_root)}")
            continue
        text = read(path)
        label = display_path(path, repo_root)
        require_contains(text, str(ZIP_PATH), label, findings)
        require_contains(text, PDF_NAME, label, findings)

    return findings


def audit(repo_root: Path, release_dir: Path, expected_head: str | None = None) -> list[str]:
    head = expected_head or current_git_head(repo_root)
    return audit_static_files(repo_root) + audit_release_dir(repo_root, release_dir, head)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "release_dir",
        nargs="?",
        default=str(RELEASE_DIR),
        help="Release directory to audit.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    release_dir = Path(args.release_dir)
    findings = audit(repo_root, release_dir)
    if findings:
        print("Release provenance audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print(f"Release provenance audit passed for {release_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
