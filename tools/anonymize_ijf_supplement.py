#!/usr/bin/env python3
"""Sanitize and audit the anonymous IJF replication supplement."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


TEXT_SUFFIXES = {
    "",
    ".bib",
    ".cff",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".r",
    ".sh",
    ".tex",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

REPLACEMENTS = (
    (re.compile(r"Rubczy[nń]ski", re.IGNORECASE), "Anonymous"),
    (re.compile(r"\bMaciej\b", re.IGNORECASE), "Anonymous"),
    (re.compile(r"rubczynski\.maciej@gmail\.com", re.IGNORECASE), "author@example.invalid"),
    (re.compile(r"\bMaciejR\b", re.IGNORECASE), "anonymous-review"),
    (
        re.compile(r"large-scale-demand-forecasting-benchmark", re.IGNORECASE),
        "anonymous-retail-forecasting-supplement",
    ),
    (
        re.compile(r"10\.5281/zenodo\.21338004", re.IGNORECASE),
        "historical-archive-withheld-for-review",
    ),
)

FORBIDDEN_PATTERNS = (
    re.compile(r"rubczy[nń]ski", re.IGNORECASE),
    re.compile(r"\bmaciej\b", re.IGNORECASE),
    re.compile(r"rubczynski\.maciej@gmail\.com", re.IGNORECASE),
    re.compile(r"\bmaciejr\b", re.IGNORECASE),
    re.compile(r"large-scale-demand-forecasting-benchmark", re.IGNORECASE),
    re.compile(r"10\.5281/zenodo\.21338004", re.IGNORECASE),
    re.compile(r"/Users/[^/\s]+/", re.IGNORECASE),
    re.compile(r"/home/[^/\s]+/", re.IGNORECASE),
    re.compile(r"[A-Z]:\\Users\\[^\\\s]+\\", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{40}\b", re.IGNORECASE),
)


def is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def sanitize_tree(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            continue
        if not path.is_file() or not is_text(path):
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        for pattern, replacement in REPLACEMENTS:
            text = pattern.sub(replacement, text)
        path.write_text(text, encoding="utf-8")


def audit_tree(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink():
            findings.append(f"forbidden symlink: {relative}")
            continue
        if not path.is_file() or path.name == "CHECKSUMS.txt":
            continue
        decoded = (
            ""
            if path.suffix.lower() == ".parquet"
            else path.read_bytes().decode("utf-8", errors="ignore")
        )
        if path.suffix.lower() == ".pdf":
            for command in (["pdfinfo", str(path)], ["pdftotext", str(path), "-"]):
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode != 0:
                    findings.append(f"cannot inspect PDF: {path.relative_to(root)}")
                    break
                decoded += "\n" + result.stdout
        if path.suffix.lower() == ".parquet":
            try:
                import pyarrow as arrow
                import pyarrow.parquet as parquet

                metadata = parquet.read_metadata(path)
                decoded += "\n" + str(metadata.schema)
                if metadata.metadata:
                    decoded += "\n" + "\n".join(
                        key.decode("utf-8", errors="ignore")
                        + "="
                        + value.decode("utf-8", errors="ignore")
                        for key, value in metadata.metadata.items()
                    )
                string_columns = [
                    field.name
                    for field in parquet.read_schema(path)
                    if arrow.types.is_string(field.type)
                    or arrow.types.is_large_string(field.type)
                    or arrow.types.is_binary(field.type)
                    or arrow.types.is_large_binary(field.type)
                ]
                if string_columns:
                    table = parquet.read_table(path, columns=string_columns)
                    decoded += "\n" + "\n".join(
                        value.decode("utf-8", errors="ignore")
                        if isinstance(value, bytes)
                        else str(value)
                        for column in table.columns
                        for chunk in column.chunks
                        for value in chunk.to_pylist()
                        if value is not None
                    )
            except (ImportError, OSError, ValueError) as exc:
                findings.append(f"cannot inspect Parquet metadata: {relative}: {exc}")
                continue
        relative_text = relative.as_posix()
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(decoded) or pattern.search(relative_text):
                findings.append(f"{relative}: matches {pattern.pattern}")
                break
        if path.name in {"COMMIT.txt", ".zenodo.json", ".env"}:
            findings.append(f"forbidden identity/private file: {relative}")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    if args.sanitize:
        sanitize_tree(args.root)
    findings = audit_tree(args.root)
    if findings:
        for finding in findings:
            print(finding)
        raise SystemExit(1)
    print(f"Anonymous supplement audit passed: {args.root}")


if __name__ == "__main__":
    main()
