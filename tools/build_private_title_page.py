#!/usr/bin/env python3
"""Build the private IJF title page without committing the postal address."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path


def tex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / "paper/submission/title_page.tex"
    address = os.environ.get("IJF_POSTAL_ADDRESS", "").strip()
    if not address:
        raise SystemExit("Set IJF_POSTAL_ADDRESS before building the private title page")

    with tempfile.TemporaryDirectory(prefix="ijf-title-page-") as tmp:
        tmp_path = Path(tmp)
        wrapper = (
            r"\def\CorrespondingPostalAddress{" + tex_escape(address) + "}\n"
            + f"\\input{{{source.as_posix()}}}\n"
        )
        wrapper_path = tmp_path / "title_page_private.tex"
        wrapper_path.write_text(wrapper)
        latex_environment = os.environ.copy()
        latex_environment.setdefault("SOURCE_DATE_EPOCH", "1787184000")
        latex_environment.setdefault("TZ", "UTC")
        subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                wrapper_path.name,
            ],
            cwd=tmp_path,
            check=True,
            env=latex_environment,
            stdout=subprocess.DEVNULL,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary_output: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{args.output.name}.", dir=args.output.parent, delete=False
            ) as handle:
                temporary_output = Path(handle.name)
                handle.write((tmp_path / "title_page_private.pdf").read_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_output, args.output)
        finally:
            if temporary_output is not None and temporary_output.exists():
                temporary_output.unlink()


if __name__ == "__main__":
    main()
