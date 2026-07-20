#!/usr/bin/env python3
"""Audit that the v1.12 zip can self-validate after unpacking."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


RELEASE_STEM = "zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair"
ZIP_PATH = Path("release") / f"{RELEASE_STEM}.zip"

UNPACKED_COMMANDS = [
    ["python3", "tools/audit_zenodo_metadata.py"],
    ["python3", "tools/audit_publication_log_v112.py"],
    ["python3", "tools/audit_release_manifest.py", ".."],
    ["python3", "tools/audit_release_privacy.py", ".."],
    ["python3", "tools/audit_release_provenance.py", ".."],
]


def audit_unpacked_zip(zip_path: Path) -> list[str]:
    findings: list[str] = []
    if not zip_path.is_file():
        return [f"missing release zip: {zip_path}"]

    tmpdir = Path(tempfile.mkdtemp(prefix="v112-unpacked-audit-"))
    try:
        try:
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(tmpdir)
        except zipfile.BadZipFile as exc:
            return [f"invalid zip file: {zip_path}: {exc}"]

        package_dir = tmpdir / RELEASE_STEM
        replication_dir = package_dir / "replication"
        if not replication_dir.is_dir():
            return [f"missing replication directory inside zip: {RELEASE_STEM}/replication"]

        for command in UNPACKED_COMMANDS:
            proc = subprocess.run(
                command,
                cwd=replication_dir,
                text=True,
                capture_output=True,
                check=False,
            )
            if proc.returncode != 0:
                detail = proc.stderr.strip() or proc.stdout.strip() or "no output"
                findings.append(f"{' '.join(command)} failed inside unpacked release: {detail}")
    finally:
        shutil.rmtree(tmpdir)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "zip_path",
        nargs="?",
        default=str(ZIP_PATH),
        help="Release zip to unpack and audit.",
    )
    args = parser.parse_args(argv)

    findings = audit_unpacked_zip(Path(args.zip_path))
    if findings:
        print("Unpacked release audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print(f"Unpacked release audit passed for {args.zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
