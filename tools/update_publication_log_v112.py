#!/usr/bin/env python3
"""Update the v1.12 publication log from a Zenodo uploader JSON result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


LOG_PATH = Path("docs/PUBLICATION_LOG_V1.12.md")
RELEASE_DIR = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair")
ZIP_PATH = Path(f"{RELEASE_DIR}.zip")
ASSET_NAME = "zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip"
HISTORICAL_DOI = "10.5281/zenodo.21338004"
FIELD_RE = re.compile(r"^(- (?P<label>[^:]+): )(?P<value>.*)$")
FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ZENODO_DOI_RE = re.compile(r"^10\.5281/zenodo\.[0-9]+$")
UTC_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return json.load(sys.stdin)
    return json.loads(path.read_text(encoding="utf-8"))


def set_field(text: str, label: str, value: str) -> str:
    lines = text.splitlines()
    replaced = 0
    for index, line in enumerate(lines):
        match = FIELD_RE.match(line)
        if match and match.group("label") == label:
            lines[index] = f"{match.group(1)}{value}"
            replaced += 1
    if replaced != 1:
        raise ValueError(f"expected one publication-log field {label!r}, found {replaced}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def record_url_from_payload(deposition: dict[str, Any]) -> str | None:
    html = deposition.get("html")
    if html and "zenodo.org" in html:
        return html
    record_id = deposition.get("record_id")
    if record_id:
        return f"https://zenodo.org/records/{record_id}"
    return None


def doi_from_payload(deposition: dict[str, Any]) -> str | None:
    doi = deposition.get("doi")
    if isinstance(doi, str) and doi.startswith("10.5281/zenodo."):
        return doi
    return None


def validate_commit(value: str) -> str:
    value = value.strip()
    if not FULL_COMMIT_RE.match(value):
        raise ValueError("DOI update commit must be a full 40-character git SHA")
    return value


def has_value(text: str, label: str) -> bool:
    marker = f"- {label}: "
    for line in text.splitlines():
        if line.startswith(marker):
            value = line[len(marker) :].strip()
            return bool(value and value != "TODO")
    raise ValueError(f"expected one publication-log field {label!r}, found 0")


def field_value(text: str, label: str) -> str:
    marker = f"- {label}: "
    matches = []
    for line in text.splitlines():
        if line.startswith(marker):
            matches.append(line[len(marker) :].strip())
    if len(matches) != 1:
        raise ValueError(f"expected one publication-log field {label!r}, found {len(matches)}")
    return matches[0]


def validate_payload_for_log_update(
    text: str,
    payload: dict[str, Any],
    zip_digest: str,
    sandbox: bool,
    doi_update_commit: str | None,
) -> None:
    mode = payload.get("mode")
    if mode not in {"dry-run", "draft", "published"}:
        raise ValueError(f"unexpected Zenodo JSON mode: {mode!r}")
    if mode != "dry-run":
        payload_sha = payload.get("zip_sha256")
        expected_sha = (
            field_value(text, "Asset SHA-256")
            if doi_update_commit or (not sandbox and has_value(text, "Asset SHA-256"))
            else zip_digest
        )
        if payload_sha != expected_sha:
            raise ValueError(
                f"Zenodo JSON zip_sha256 {payload_sha!r} does not match expected uploaded release zip {expected_sha}"
            )
        asset_name = payload.get("asset_name")
        if asset_name != ASSET_NAME:
            raise ValueError(
                f"Zenodo JSON asset_name {asset_name!r} does not match expected {ASSET_NAME}"
            )
    if sandbox or mode != "published":
        return

    deposition = payload.get("deposition") or {}
    doi = doi_from_payload(deposition)
    record_url = record_url_from_payload(deposition)
    published_at = payload.get("published_at_utc")
    if not doi or not ZENODO_DOI_RE.fullmatch(doi):
        raise ValueError("published Zenodo JSON does not include a production Zenodo DOI")
    if doi == HISTORICAL_DOI:
        raise ValueError("published Zenodo JSON uses the historical v1.0 DOI as the v1.12 DOI")
    if not record_url or not record_url.startswith("https://zenodo.org/records/"):
        raise ValueError("published Zenodo JSON does not include a production record URL")
    if not isinstance(published_at, str) or not UTC_TIMESTAMP_RE.fullmatch(published_at):
        raise ValueError("published Zenodo JSON does not include an ISO-8601 UTC published_at_utc")
    if doi_update_commit and not doi_from_payload(deposition):
        raise ValueError("cannot record DOI metadata commit without a published DOI")


def update_log_text(
    text: str,
    payload: dict[str, Any],
    current_commit: str,
    zip_digest: str,
    sandbox: bool,
    doi_update_commit: str | None = None,
) -> str:
    deposition = payload.get("deposition") or {}
    deposition_id = deposition.get("id")
    record_url = record_url_from_payload(deposition)
    doi = doi_from_payload(deposition)

    if doi_update_commit and (
        not has_value(text, "Target commit") or not has_value(text, "Asset SHA-256")
    ):
        raise ValueError(
            "record the Zenodo-uploaded Target commit and Asset SHA-256 before "
            "recording the DOI metadata update commit"
        )
    validate_payload_for_log_update(text, payload, zip_digest, sandbox, doi_update_commit)

    if payload.get("mode") != "dry-run" and not doi_update_commit:
        if not sandbox and not has_value(text, "Target commit"):
            text = set_field(text, "Target commit", current_commit)
        if not sandbox and not has_value(text, "Asset SHA-256"):
            text = set_field(text, "Asset SHA-256", zip_digest)

    if sandbox:
        if deposition_id is not None:
            text = set_field(text, "Sandbox deposition ID", str(deposition_id))
        return text

    if deposition_id is not None:
        text = set_field(text, "Production deposition ID", str(deposition_id))
    if record_url:
        text = set_field(text, "Production record URL", record_url)
    if doi:
        text = set_field(text, "Production DOI", doi)
        text = set_field(text, "Production DOI URL", f"https://doi.org/{doi}")
    if doi_update_commit:
        text = set_field(text, "DOI metadata update commit", doi_update_commit)
    published_at = payload.get("published_at_utc")
    if isinstance(published_at, str) and payload.get("mode") == "published":
        text = set_field(text, "Published at", published_at)
    return text


def planned_update(
    repo_root: Path,
    payload: dict[str, Any],
    sandbox: bool,
    doi_update_commit: str | None = None,
) -> str:
    log_path = repo_root / LOG_PATH
    zip_path = repo_root / ZIP_PATH
    current_commit = run(["git", "rev-parse", "HEAD"], repo_root)
    if doi_update_commit:
        doi_update_commit = validate_commit(doi_update_commit)
    return update_log_text(
        log_path.read_text(encoding="utf-8"),
        payload,
        current_commit=current_commit,
        zip_digest=sha256(zip_path),
        sandbox=sandbox,
        doi_update_commit=doi_update_commit,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zenodo-json",
        type=Path,
        help="Path to JSON output from tools/zenodo_upload_v112.py. Reads stdin if omitted.",
    )
    parser.add_argument("--sandbox", action="store_true", help="Update sandbox fields.")
    parser.add_argument(
        "--doi-update-commit",
        help="Full SHA of the commit that applied the minted DOI to citation/manuscript metadata.",
    )
    parser.add_argument("--apply", action="store_true", help="Write the publication log.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    try:
        payload = load_json(args.zenodo_json)
        updated = planned_update(
            repo_root,
            payload,
            sandbox=args.sandbox,
            doi_update_commit=args.doi_update_commit,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Publication log update failed: {exc}", file=sys.stderr)
        return 1

    original = (repo_root / LOG_PATH).read_text(encoding="utf-8")
    changed = updated != original
    mode = "apply" if args.apply else "dry-run"
    print(f"Publication log update {mode}: changed={str(changed).lower()}")
    if args.apply and changed:
        (repo_root / LOG_PATH).write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
