#!/usr/bin/env python3
"""Fail when the double-anonymized manuscript PDF leaks author identity."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


FORBIDDEN = (
    "Maciej Rubczynski",
    "MaciejR",
    "rubczynski.maciej@gmail.com",
    "10.5281/zenodo.21338004",
    "large-scale-demand-forecasting-benchmark",
)


def command_output(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout


def audit(pdf: Path) -> list[str]:
    findings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ijf-anonymity-") as tmp:
        text_path = Path(tmp) / "manuscript.txt"
        subprocess.run(["pdftotext", str(pdf), str(text_path)], check=True)
        combined = text_path.read_text(errors="replace") + "\n" + command_output(
            "pdfinfo", str(pdf)
        )
    folded = combined.casefold()
    for term in FORBIDDEN:
        if term.casefold() in folded:
            findings.append(f"identity leak in anonymous PDF: {term}")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    findings = audit(args.pdf)
    if findings:
        for finding in findings:
            print(finding)
        raise SystemExit(1)
    print(f"Anonymous manuscript audit passed: {args.pdf}")


if __name__ == "__main__":
    main()
