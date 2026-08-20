#!/usr/bin/env python3
"""Audit v1.21 submission metadata and built package provenance."""

from __future__ import annotations

import argparse
import hashlib
import re
import stat
import subprocess
import zipfile
from pathlib import Path

from anonymize_ijf_supplement import audit_tree
from audit_release_privacy import audit_release as audit_privacy


VERSION = "v1.21"
RELEASE_DATE = "2026-08-20"
REPO_URL = "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark"
PUBLIC_STEM = "v1.21-ijf-submission-ready"
ANON_STEM = "v1.21-ijf-anonymous-supplement"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def audit_static(repo_root: Path) -> list[str]:
    findings: list[str] = []
    citation = read(repo_root / "CITATION.cff")
    readme = read(repo_root / "README.md")
    manuscript = read(repo_root / "paper/latex/main.tex")
    release_notes = read(repo_root / "docs/RELEASE_V1.21.md")
    builder = read(repo_root / "tools/build_v121_release.sh")

    checks = (
        (citation, r'^version:\s*"v1\.21"$', "CITATION version"),
        (citation, r'^date-released:\s*"2026-08-20"$', "CITATION date"),
        (citation, re.escape(f"{REPO_URL}/releases/tag/{VERSION}"), "CITATION URL"),
        (readme, re.escape(f"release/v1.21/{PUBLIC_STEM}.zip"), "README public package"),
        (readme, re.escape(f"{REPO_URL}/releases/tag/{VERSION}"), "README release URL"),
        (manuscript, re.escape(f"{REPO_URL}/releases/tag/{VERSION}"), "manuscript release URL"),
        (release_notes, re.escape(f"release/v1.21/{PUBLIC_STEM}.zip"), "release notes package"),
        (builder, re.escape(PUBLIC_STEM), "builder public stem"),
        (builder, re.escape(ANON_STEM), "builder anonymous stem"),
        (builder, "git archive --format=tar HEAD", "tracked-files-only packaging"),
        (builder, "create_deterministic_zip.py", "deterministic ZIP builder"),
        (builder, "anonymize_ijf_supplement.py", "anonymous supplement audit"),
    )
    for text, pattern, label in checks:
        if not re.search(pattern, text, re.MULTILINE):
            findings.append(f"{label}: missing {pattern!r}")
    return findings


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_checksums(package_dir: Path) -> list[str]:
    findings: list[str] = []
    manifest = package_dir / "CHECKSUMS.txt"
    if not manifest.is_file():
        return [f"missing checksum manifest: {manifest}"]
    listed: set[str] = set()
    for line in read(manifest).splitlines():
        try:
            expected, relative = line.split("  ", 1)
        except ValueError:
            findings.append(f"malformed checksum line: {line}")
            continue
        relative = relative.removeprefix("./")
        listed.add(relative)
        path = package_dir / relative
        if not path.is_file() or sha256(path) != expected:
            findings.append(f"checksum mismatch: {relative}")
    actual = {
        path.relative_to(package_dir).as_posix()
        for path in package_dir.rglob("*")
        if path.is_file() and not path.is_symlink() and path.name != "CHECKSUMS.txt"
    }
    if listed != actual:
        findings.append("checksum manifest does not cover exactly all packaged files")
    return findings


def audit_package_hygiene(package_dir: Path) -> list[str]:
    findings: list[str] = []
    forbidden_parts = {
        ".cache",
        ".env",
        ".git",
        ".pytest_cache",
        ".zenodo.json",
        "__pycache__",
        "mlruns",
        "logs",
    }
    forbidden_suffixes = {".ckpt", ".pt", ".pth", ".safetensors"}
    for path in package_dir.rglob("*"):
        relative = path.relative_to(package_dir)
        if path.is_symlink():
            findings.append(f"forbidden packaged symlink: {relative}")
            continue
        if any(part in forbidden_parts or part.startswith("smoke_") for part in relative.parts):
            findings.append(f"forbidden packaged path: {relative}")
        if path.is_file() and path.suffix.lower() in forbidden_suffixes:
            findings.append(f"forbidden packaged model file: {relative}")
        if path.is_file() and path.stat().st_size > 250 * 1024 * 1024:
            findings.append(f"unexpected file over 250 MiB: {relative}")
        if "benchmark/results/fev_bench_official" in relative.as_posix():
            findings.append(f"full fev-bench prediction tree included: {relative}")
        if relative.as_posix().endswith("paper/submission/title_page.pdf"):
            findings.append(f"private title-page PDF included: {relative}")
        if relative.as_posix().startswith("replication/data/raw/") or \
           relative.as_posix().startswith("data/raw/"):
            findings.append(f"raw data included: {relative}")
    findings.extend(audit_privacy(package_dir))
    return findings


def audit_zip_matches_dir(zip_path: Path, package_dir: Path) -> list[str]:
    if not zip_path.is_file():
        return [f"missing ZIP: {zip_path.name}"]
    findings: list[str] = []
    expected = {
        f"{package_dir.name}/{path.relative_to(package_dir).as_posix()}": path
        for path in package_dir.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    try:
        with zipfile.ZipFile(zip_path) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            actual_names = {info.filename for info in infos}
            if actual_names != set(expected):
                findings.append(f"ZIP entries do not match directory: {zip_path.name}")
            for info in infos:
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    findings.append(f"ZIP contains symlink: {info.filename}")
                source = expected.get(info.filename)
                if source is not None and archive.read(info) != source.read_bytes():
                    findings.append(f"ZIP content mismatch: {info.filename}")
    except (OSError, zipfile.BadZipFile) as exc:
        findings.append(f"invalid ZIP {zip_path.name}: {exc}")
    return findings


def audit_package_dirs(
    public_dir: Path, anon_dir: Path, expected_head: str
) -> list[str]:
    findings: list[str] = []
    required_public = (
        "COMMIT.txt",
        "CHECKSUMS.txt",
        "README.md",
        "manuscript/manuscript-public-v1.21.pdf",
        "manuscript/manuscript-double-anonymized-v1.21.pdf",
        "submission/cover_letter.pdf",
        "submission/highlights.txt",
        "submission/declaration_of_interests.docx",
        "submission/title_page.tex",
    )
    required_anonymous = (
        "ARTIFACTS.md",
        "CHECKSUMS.txt",
        "README.md",
        "REPRODUCING.md",
        "SOURCE_STATE.txt",
        "analysis/extraction_schema.csv",
        "analysis/study_characteristics.csv",
        "benchmark/results/local_fm_sweep.csv",
        "data/m5_200trial/artifact_manifest.json",
        "tools/validate_m5_200trial_artifact.py",
    )
    if not public_dir.is_dir():
        findings.append(f"missing public package directory: {public_dir}")
    if not anon_dir.is_dir():
        findings.append(f"missing anonymous package directory: {anon_dir}")
    for relative in required_public:
        if not (public_dir / relative).is_file():
            findings.append(f"missing public package file: {relative}")
    for relative in required_anonymous:
        if not (anon_dir / relative).is_file():
            findings.append(f"missing anonymous package file: {relative}")
    if public_dir.is_dir():
        findings.extend(audit_checksums(public_dir))
        findings.extend(audit_package_hygiene(public_dir))
        commit_file = public_dir / "COMMIT.txt"
        if commit_file.is_file() and read(commit_file).strip() != expected_head:
            findings.append("public COMMIT.txt does not match HEAD")
    if anon_dir.is_dir():
        findings.extend(audit_checksums(anon_dir))
        findings.extend(audit_package_hygiene(anon_dir))
        findings.extend(audit_tree(anon_dir))
        if (anon_dir / "COMMIT.txt").exists():
            findings.append("anonymous package exposes COMMIT.txt")
    return findings


def audit_packages(repo_root: Path) -> list[str]:
    findings = audit_static(repo_root)
    release_root = repo_root / "release" / "v1.21"
    public_dir = release_root / PUBLIC_STEM
    anon_dir = release_root / ANON_STEM
    expected_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
    ).strip()
    findings.extend(audit_package_dirs(public_dir, anon_dir, expected_head))
    findings.extend(audit_zip_matches_dir(release_root / f"{PUBLIC_STEM}.zip", public_dir))
    findings.extend(audit_zip_matches_dir(release_root / f"{ANON_STEM}.zip", anon_dir))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--public-dir", type=Path)
    parser.add_argument("--anon-dir", type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--public-zip", type=Path)
    parser.add_argument("--anon-zip", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if any((args.public_dir, args.anon_dir, args.expected_head, args.public_zip, args.anon_zip)):
        if not (args.public_dir and args.anon_dir and args.expected_head):
            parser.error("--public-dir, --anon-dir, and --expected-head are required together")
        findings = audit_static(root) + audit_package_dirs(
            args.public_dir, args.anon_dir, args.expected_head
        )
        if args.public_zip:
            findings.extend(audit_zip_matches_dir(args.public_zip, args.public_dir))
        if args.anon_zip:
            findings.extend(audit_zip_matches_dir(args.anon_zip, args.anon_dir))
    else:
        findings = audit_static(root) if args.static_only else audit_packages(root)
    if findings:
        for finding in findings:
            print(finding)
        raise SystemExit(1)
    print("v1.21 release audit passed")


if __name__ == "__main__":
    main()
