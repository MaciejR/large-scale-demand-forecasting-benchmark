#!/usr/bin/env python3
"""Apply a minted v1.12 Zenodo DOI to citation and release metadata files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


HISTORICAL_DOI = "10.5281/zenodo.21338004"
GITHUB_RELEASE_URL = (
    "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.12"
)
DOI_RE = re.compile(r"^10\.5281/zenodo\.[0-9]+$")


def validate_doi(doi: str) -> str:
    doi = doi.strip()
    if not DOI_RE.match(doi):
        raise ValueError("DOI must look like 10.5281/zenodo.<digits>")
    if doi == HISTORICAL_DOI:
        raise ValueError("refusing to use the historical v1.0 DOI as the v1.12 DOI")
    return doi


def replace_once(text: str, old: str, new: str, path: Path) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{path}: expected one occurrence of {old!r}, found {count}")
    return text.replace(old, new)


def already_updated(text: str, doi: str, required: list[str], forbidden: list[str]) -> bool:
    doi_url = f"https://doi.org/{doi}"
    return (
        doi in text
        and doi_url in text
        and all(marker in text for marker in required)
        and not any(marker in text for marker in forbidden)
    )


def update_readme(text: str, doi: str) -> str:
    doi_url = f"https://doi.org/{doi}"
    if already_updated(
        text,
        doi,
        required=[
            f"[![DOI](https://zenodo.org/badge/DOI/{doi}.svg)]({doi_url})",
            "For the current repair package, cite the Zenodo archive:",
            f"Zenodo. {doi_url}",
            f"doi          = {{{doi}}}",
            f"url          = {{{doi_url}}}",
        ],
        forbidden=[
            "corresponding Zenodo archive once minted",
            "The current Zenodo-ready repair package is published as GitHub release",
        ],
    ):
        return text
    text = replace_once(
        text,
        (
            f"[![DOI](https://zenodo.org/badge/DOI/{HISTORICAL_DOI}.svg)]"
            f"(https://doi.org/{HISTORICAL_DOI})"
        ),
        f"[![DOI](https://zenodo.org/badge/DOI/{doi}.svg)]({doi_url})",
        Path("README.md"),
    )
    text = replace_once(
        text,
        "For the current repair package, cite the repository version or the\n"
        "corresponding Zenodo archive once minted:",
        "For the current repair package, cite the Zenodo archive:",
        Path("README.md"),
    )
    text = replace_once(
        text,
        f"GitHub. {GITHUB_RELEASE_URL}",
        f"Zenodo. {doi_url}",
        Path("README.md"),
    )
    text = replace_once(
        text,
        f"  url          = {{{GITHUB_RELEASE_URL}}}",
        f"  publisher    = {{Zenodo}},\n  doi          = {{{doi}}},\n  url          = {{{doi_url}}}",
        Path("README.md"),
    )
    text = replace_once(
        text,
        "The current Zenodo-ready repair package is published as GitHub release",
        "The current repair package is archived on Zenodo and mirrored as GitHub release",
        Path("README.md"),
    )
    return text


def update_citation(text: str, doi: str) -> str:
    doi_url = f"https://doi.org/{doi}"
    if already_updated(
        text,
        doi,
        required=[f'doi: "{doi}"', f'url: "{doi_url}"'],
        forbidden=["when minted", f'url: "{GITHUB_RELEASE_URL}"'],
    ):
        return text
    text = replace_once(
        text,
        'message: "If you use the current repair package, cite this repository version or the corresponding Zenodo archive when minted."',
        'message: "If you use the current repair package, cite the corresponding Zenodo archive."',
        Path("CITATION.cff"),
    )
    text = replace_once(
        text,
        f'url: "{GITHUB_RELEASE_URL}"',
        f'doi: "{doi}"\nurl: "{doi_url}"',
        Path("CITATION.cff"),
    )
    return text


def update_main_tex(text: str, doi: str) -> str:
    doi_url = f"https://doi.org/{doi}"
    if already_updated(
        text,
        doi,
        required=[
            f"v1.12 is archived at \\url{{{doi_url}}}",
            f"\\url{{{GITHUB_RELEASE_URL}}}",
        ],
        forbidden=["Zenodo-ready archive under \\path{release/}"],
    ):
        return text
    old = (
        "the release package corresponding to this manuscript is prepared as a\n"
        "versioned Zenodo-ready archive under \\path{release/} rather than overwriting the\n"
        "historical snapshot, and is published as GitHub release v1.12 at\n"
        f"\\url{{{GITHUB_RELEASE_URL}}}."
    )
    new = (
        "the release package corresponding to this manuscript is archived as a\n"
        "separate Zenodo record rather than overwriting the historical snapshot.  Version\n"
        f"v1.12 is archived at \\url{{{doi_url}}} and mirrored as GitHub release v1.12 at\n"
        f"\\url{{{GITHUB_RELEASE_URL}}}."
    )
    return replace_once(text, old, new, Path("paper/latex/main.tex"))


def update_release_notes(text: str, doi: str) -> str:
    doi_line = f"Zenodo DOI: https://doi.org/{doi}"
    if doi_line in text:
        return text
    marker = "Release commit: recorded in the release package `COMMIT.txt`.\n"
    return replace_once(text, marker, f"{marker}{doi_line}\n", Path("docs/RELEASE_V1.12.md"))


UPDATERS = {
    Path("README.md"): update_readme,
    Path("CITATION.cff"): update_citation,
    Path("paper/latex/main.tex"): update_main_tex,
    Path("docs/RELEASE_V1.12.md"): update_release_notes,
}


def planned_updates(repo_root: Path, doi: str) -> dict[Path, str]:
    doi = validate_doi(doi)
    updates: dict[Path, str] = {}
    for relative_path, updater in UPDATERS.items():
        path = repo_root / relative_path
        original = path.read_text(encoding="utf-8")
        updated = updater(original, doi)
        if updated != original:
            updates[relative_path] = updated
    return updates


def apply_updates(repo_root: Path, updates: dict[Path, str]) -> None:
    for relative_path, updated in updates.items():
        (repo_root / relative_path).write_text(updated, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doi", required=True, help="Minted v1.12 DOI, e.g. 10.5281/zenodo.12345678")
    parser.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    try:
        updates = planned_updates(repo_root, args.doi)
    except ValueError as exc:
        print(f"DOI update failed: {exc}", file=sys.stderr)
        return 1

    mode = "apply" if args.apply else "dry-run"
    print(f"v1.12 DOI update {mode}: {len(updates)} file(s) would change")
    for path in updates:
        print(f"  - {path}")
    if args.apply:
        apply_updates(repo_root, updates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
