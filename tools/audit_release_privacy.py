#!/usr/bin/env python3
"""Scan a release directory for private files, local paths, and token-shaped text."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_RELEASE_DIR = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair")

FORBIDDEN_PATH_PARTS = {
    ".env",
    ".DS_Store",
    "__pycache__",
    ".pytest_cache",
    "data/raw",
    "mlruns",
    "logs",
    "benchmark/results/fev_bench_official",
    "source_b_v1_11_timesfm25_m5_rohlik_100_batched",
}

FORBIDDEN_NAME_PATTERNS = [
    re.compile(r"Umowa.*\.pdf$", re.IGNORECASE),
    re.compile(r".*\.(?:pyc|log|ckpt|pt|pth|safetensors)$", re.IGNORECASE),
]

SECRET_PATTERNS = [
    ("openai_api_key", re.compile(r"\bsk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("huggingface_token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("aws_secret_assignment", re.compile(r"\bAWS_SECRET_ACCESS_KEY\s*=\s*['\"]?[A-Za-z0-9/+=]{20,}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
]

LOCAL_PATH_PATTERNS = [
    ("macos_home_path", re.compile("/" + r"Users/[A-Za-z0-9._-]+/")),
    ("linux_home_path", re.compile("/" + r"home/[A-Za-z0-9._-]+/")),
    ("sandbox_path", re.compile(r"(?:sandbox:)?" + "/" + r"mnt/data/")),
    ("windows_home_path", re.compile(r"[A-Za-z]:\\Users\\[^\\]+\\", re.IGNORECASE)),
]

BINARY_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".zip",
    ".gz",
    ".parquet",
}


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def audit_paths(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        rel = relative_posix(path, root)
        if path.is_symlink():
            findings.append(f"path:{rel}: forbidden symlink")
            continue
        parts = path.relative_to(root).parts
        for forbidden in FORBIDDEN_PATH_PARTS:
            if (
                ("/" in forbidden and forbidden in rel)
                or ("/" not in forbidden and forbidden in parts)
            ):
                findings.append(f"path:{rel}: forbidden path component {forbidden}")
        if path.is_file():
            for pattern in FORBIDDEN_NAME_PATTERNS:
                if pattern.fullmatch(path.name):
                    findings.append(f"path:{rel}: forbidden file name")
    return findings


def iter_text_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for lineno, line in enumerate(handle, start=1):
            yield lineno, line.rstrip("\n")


def audit_text(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        rel = relative_posix(path, root)
        for lineno, line in iter_text_lines(path):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(f"text:{rel}:{lineno}: token-shaped secret ({label})")
            for label, pattern in LOCAL_PATH_PATTERNS:
                if pattern.search(line):
                    findings.append(f"text:{rel}:{lineno}: local path ({label})")
    return findings


def audit_release(root: Path) -> list[str]:
    if not root.exists():
        return [f"path:{root}: release directory does not exist"]
    if not root.is_dir():
        return [f"path:{root}: expected a directory"]
    return audit_paths(root) + audit_text(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "release_dir",
        nargs="?",
        default=str(DEFAULT_RELEASE_DIR),
        help="Release directory to scan.",
    )
    args = parser.parse_args(argv)

    root = Path(args.release_dir)
    findings = audit_release(root)
    if findings:
        print("Release privacy audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print(f"Release privacy audit passed for {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
