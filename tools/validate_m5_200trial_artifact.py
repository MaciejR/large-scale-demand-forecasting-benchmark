#!/usr/bin/env python3
"""Validate the allow-listed M5 LightGBM 200-trial sensitivity artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.source_b_m5_200trial_sensitivity import load_manifest, validate_artifact


DEFAULT_MANIFEST = ROOT / "data" / "m5_200trial" / "artifact_manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--allow-private-pdfs",
        action="store_true",
        help="Skip the workspace scan for untracked/private PDF files.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    manifest = load_manifest(Path(args.manifest))
    try:
        run_dirs = validate_artifact(manifest, root)
        if not args.allow_private_pdfs:
            private_pdfs = [
                path
                for path in root.glob("*Umowa*.pdf")
                if path.is_file()
            ]
            if private_pdfs:
                joined = "\n".join(str(path) for path in private_pdfs)
                raise ValueError(f"Private/legal PDF files remain in repo root:\n{joined}")
    except Exception as exc:
        print(f"M5 200-trial artifact validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"M5 200-trial artifact validation passed for {len(run_dirs)} runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
