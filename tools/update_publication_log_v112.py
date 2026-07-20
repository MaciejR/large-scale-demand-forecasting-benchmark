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
FIELD_RE = re.compile(r"^(- (?P<label>[^:]+): )(?P<value>.*)$")


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


def update_log_text(
    text: str,
    payload: dict[str, Any],
    current_commit: str,
    zip_digest: str,
    sandbox: bool,
) -> str:
    deposition = payload.get("deposition") or {}
    deposition_id = deposition.get("id")
    record_url = record_url_from_payload(deposition)
    doi = doi_from_payload(deposition)

    text = set_field(text, "Target commit", current_commit)
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
    if payload.get("mode") == "published":
        text = set_field(text, "Published at", "recorded by Zenodo")
    return text


def planned_update(repo_root: Path, payload: dict[str, Any], sandbox: bool) -> str:
    log_path = repo_root / LOG_PATH
    zip_path = repo_root / ZIP_PATH
    current_commit = run(["git", "rev-parse", "HEAD"], repo_root)
    return update_log_text(
        log_path.read_text(encoding="utf-8"),
        payload,
        current_commit=current_commit,
        zip_digest=sha256(zip_path),
        sandbox=sandbox,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zenodo-json",
        type=Path,
        help="Path to JSON output from tools/zenodo_upload_v112.py. Reads stdin if omitted.",
    )
    parser.add_argument("--sandbox", action="store_true", help="Update sandbox fields.")
    parser.add_argument("--apply", action="store_true", help="Write the publication log.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    try:
        payload = load_json(args.zenodo_json)
        updated = planned_update(repo_root, payload, sandbox=args.sandbox)
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
