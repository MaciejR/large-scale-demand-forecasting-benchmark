#!/usr/bin/env python3
"""Check LaTeX citation keys against the BibTeX database."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LATEX_DIR = ROOT / "paper" / "latex"
BIB_PATH = ROOT / "paper" / "references.bib"

CITE_RE = re.compile(
    r"\\(?:citep|citet|citealp|citeauthor|citeyear|cite|nocite)"
    r"(?:\s*\[[^\]]*\])*"
    r"\s*\{([^{}]+)\}",
    re.MULTILINE,
)
BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)


def parse_bib_keys() -> tuple[set[str], list[str]]:
    text = BIB_PATH.read_text()
    keys = BIB_KEY_RE.findall(text)
    seen: set[str] = set()
    duplicates: list[str] = []
    for key in keys:
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    return seen, duplicates


def parse_citation_keys() -> dict[str, set[str]]:
    citations: dict[str, set[str]] = {}
    for path in sorted(LATEX_DIR.glob("*.tex")):
        text = path.read_text()
        keys: set[str] = set()
        for match in CITE_RE.finditer(text):
            keys.update(
                key.strip()
                for key in match.group(1).replace("\n", " ").split(",")
                if key.strip() and key.strip() != "*"
            )
        if keys:
            citations[str(path.relative_to(ROOT))] = keys
    return citations


def main() -> int:
    bib_keys, duplicates = parse_bib_keys()
    citations_by_file = parse_citation_keys()
    cited_keys = set().union(*citations_by_file.values()) if citations_by_file else set()
    missing = sorted(cited_keys - bib_keys)

    if duplicates:
        print("Duplicate BibTeX keys:", file=sys.stderr)
        for key in sorted(set(duplicates)):
            print(f"  {key}", file=sys.stderr)
    if missing:
        print("Citation keys missing from paper/references.bib:", file=sys.stderr)
        for key in missing:
            locations = [
                path for path, keys in citations_by_file.items() if key in keys
            ]
            print(f"  {key}: {', '.join(locations)}", file=sys.stderr)

    if duplicates or missing:
        return 1

    print(
        f"Citation audit passed: {len(cited_keys)} cited keys, "
        f"{len(bib_keys)} BibTeX entries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
