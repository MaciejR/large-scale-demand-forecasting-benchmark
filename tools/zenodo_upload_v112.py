#!/usr/bin/env python3
"""Create or update a Zenodo draft for the v1.12 release package."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

import audit_zenodo_upload_readiness


ZIP_PATH = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip")
METADATA_PATH = Path("docs/ZENODO_METADATA_V1.12.json")
ASSET_NAME = "zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip"
ZENODO_API = "https://zenodo.org/api"
SANDBOX_API = "https://sandbox.zenodo.org/api"
ZIP_SHA_NOTE_PREFIX = "Uploaded archive SHA-256"


class ZenodoError(RuntimeError):
    """Raised when Zenodo returns an unexpected response."""


def load_metadata(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def token_from_env(env_names: list[str]) -> str | None:
    for name in env_names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def checked_json(response: requests.Response, expected: set[int], action: str) -> dict[str, Any]:
    if response.status_code not in expected:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise ZenodoError(f"{action} failed with HTTP {response.status_code}: {detail}")
    try:
        return response.json()
    except ValueError as exc:
        raise ZenodoError(f"{action} returned non-JSON response") from exc


def create_deposition(session: requests.Session, api_base: str) -> dict[str, Any]:
    response = session.post(f"{api_base}/deposit/depositions", json={})
    return checked_json(response, {201}, "create deposition")


def retrieve_deposition(
    session: requests.Session,
    api_base: str,
    deposition_id: str,
) -> dict[str, Any]:
    response = session.get(f"{api_base}/deposit/depositions/{deposition_id}")
    return checked_json(response, {200}, "retrieve deposition")


def upload_file(
    session: requests.Session,
    bucket_url: str,
    zip_path: Path,
    asset_name: str,
) -> dict[str, Any]:
    with zip_path.open("rb") as handle:
        response = session.put(f"{bucket_url}/{asset_name}", data=handle)
    return checked_json(response, {200, 201}, "upload file")


def update_metadata(
    session: requests.Session,
    api_base: str,
    deposition_id: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    response = session.put(
        f"{api_base}/deposit/depositions/{deposition_id}",
        json={"metadata": metadata},
    )
    return checked_json(response, {200}, "update metadata")


def publish_deposition(
    session: requests.Session,
    api_base: str,
    deposition_id: str,
) -> dict[str, Any]:
    response = session.post(f"{api_base}/deposit/depositions/{deposition_id}/actions/publish")
    return checked_json(response, {202}, "publish deposition")


def deposition_summary(payload: dict[str, Any]) -> dict[str, Any]:
    links = payload.get("links", {})
    metadata = payload.get("metadata", {})
    return {
        "id": payload.get("id"),
        "record_id": payload.get("record_id"),
        "state": payload.get("state"),
        "submitted": payload.get("submitted"),
        "title": payload.get("title") or metadata.get("title"),
        "html": links.get("html") or links.get("latest_draft_html"),
        "doi": metadata.get("doi") or metadata.get("prereserve_doi", {}).get("doi"),
    }


def metadata_with_zip_sha(metadata: dict[str, Any], zip_path: Path) -> dict[str, Any]:
    result = copy.deepcopy(metadata)
    zip_digest = sha256(zip_path)
    note = f"{ZIP_SHA_NOTE_PREFIX}: {zip_digest}; uploaded asset: {ASSET_NAME}."
    existing_notes = result.get("notes", "")
    if ZIP_SHA_NOTE_PREFIX in existing_notes:
        return result
    result["notes"] = f"{existing_notes.rstrip()} {note}".strip()
    return result


def dry_run_report(
    api_base: str,
    zip_path: Path,
    metadata_path: Path,
    metadata: dict[str, Any],
    deposition_id: str | None,
    publish: bool,
) -> dict[str, Any]:
    return {
        "mode": "dry-run",
        "api_base": api_base,
        "deposition_id": deposition_id,
        "zip": str(zip_path),
        "zip_size": zip_path.stat().st_size,
        "metadata": str(metadata_path),
        "title": metadata.get("title"),
        "version": metadata.get("version"),
        "asset_name": ASSET_NAME,
        "zip_sha256": sha256(zip_path),
        "metadata_notes_include_zip_sha": ZIP_SHA_NOTE_PREFIX in metadata.get("notes", ""),
        "would_publish": publish,
    }


def write_json_result(result: dict[str, Any], output_path: Path | None) -> str:
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if output_path is not None:
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
    return rendered


def upload(
    repo_root: Path,
    api_base: str,
    zip_path: Path,
    metadata_path: Path,
    deposition_id: str | None,
    publish: bool,
    dry_run: bool,
    token_env: list[str],
) -> dict[str, Any]:
    readiness = audit_zenodo_upload_readiness.audit(
        repo_root,
        require_token=not dry_run,
        token_env_vars=tuple(token_env),
    )
    if readiness:
        raise ZenodoError("readiness audit failed: " + "; ".join(readiness))

    metadata = metadata_with_zip_sha(load_metadata(metadata_path), zip_path)
    if dry_run:
        return dry_run_report(api_base, zip_path, metadata_path, metadata, deposition_id, publish)

    token = token_from_env(token_env)
    if token is None:
        raise ZenodoError("missing Zenodo token")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    deposition = (
        retrieve_deposition(session, api_base, deposition_id)
        if deposition_id
        else create_deposition(session, api_base)
    )
    deposition_id = str(deposition["id"])
    bucket_url = deposition.get("links", {}).get("bucket")
    if not bucket_url:
        raise ZenodoError("deposition response did not include links.bucket")

    upload_file(session, bucket_url, zip_path, ASSET_NAME)
    updated = update_metadata(session, api_base, deposition_id, metadata)
    result = {
        "mode": "published" if publish else "draft",
        "deposition": deposition_summary(updated),
        "asset_name": ASSET_NAME,
        "zip": str(zip_path),
    }
    if publish:
        result["deposition"] = deposition_summary(
            publish_deposition(session, api_base, deposition_id)
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deposition-id", help="Existing unpublished deposition ID to update.")
    parser.add_argument("--publish", action="store_true", help="Publish after uploading.")
    parser.add_argument("--sandbox", action="store_true", help="Use sandbox.zenodo.org.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print planned actions.")
    parser.add_argument("--output-json", type=Path, help="Also write the JSON result to this path.")
    parser.add_argument("--zip", default=str(ZIP_PATH), help="Release zip path.")
    parser.add_argument("--metadata", default=str(METADATA_PATH), help="Zenodo metadata JSON.")
    parser.add_argument(
        "--token-env",
        action="append",
        default=[],
        help="Environment variable containing the Zenodo token. May be repeated.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    api_base = SANDBOX_API if args.sandbox else ZENODO_API
    if args.token_env:
        token_env = args.token_env
    elif args.sandbox:
        token_env = list(audit_zenodo_upload_readiness.SANDBOX_TOKEN_ENV_VARS)
    else:
        token_env = list(audit_zenodo_upload_readiness.TOKEN_ENV_VARS)

    try:
        result = upload(
            repo_root=repo_root,
            api_base=api_base,
            zip_path=repo_root / args.zip,
            metadata_path=repo_root / args.metadata,
            deposition_id=args.deposition_id,
            publish=args.publish,
            dry_run=args.dry_run,
            token_env=token_env,
        )
    except ZenodoError as exc:
        print(f"Zenodo upload failed: {exc}", file=sys.stderr)
        return 1

    print(write_json_result(result, args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
