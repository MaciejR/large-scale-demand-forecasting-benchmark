#!/usr/bin/env python3
"""Create a byte-reproducible ZIP archive from a directory tree."""

from __future__ import annotations

import argparse
import stat
import zipfile
from pathlib import Path


FIXED_TIMESTAMP = (2026, 8, 20, 0, 0, 0)


def create_zip(source_dir: Path, output: Path) -> None:
    source_dir = source_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = sorted(source_dir.rglob("*"), key=lambda item: item.as_posix())
    symlinks = [path.relative_to(source_dir) for path in paths if path.is_symlink()]
    if symlinks:
        raise ValueError(f"refusing to archive symlink: {symlinks[0]}")
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in paths:
            if not path.is_file():
                continue
            arcname = f"{source_dir.name}/{path.relative_to(source_dir).as_posix()}"
            info = zipfile.ZipInfo(arcname, FIXED_TIMESTAMP)
            info.create_system = 3
            mode = 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    create_zip(args.source_dir, args.output)


if __name__ == "__main__":
    main()
