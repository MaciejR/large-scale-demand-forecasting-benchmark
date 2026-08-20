#!/usr/bin/env python3
"""Select the no-conflicts option in Elsevier's declaration DOCX template."""

from __future__ import annotations

import argparse
import tempfile
import urllib.request
import zipfile
from pathlib import Path


TEMPLATE_URL = (
    "https://www.elsevier.com/__data/promis_misc/"
    "declaration-of-competing-interests.docx"
)


def build(output: Path, template: Path | None = None) -> None:
    if template is None:
        with tempfile.TemporaryDirectory(prefix="ijf-declaration-") as tmp:
            downloaded = Path(tmp) / "template.docx"
            urllib.request.urlretrieve(TEMPLATE_URL, downloaded)
            _patch(downloaded, output)
    else:
        _patch(template, output)


def _patch(template: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(template) as source, zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED
    ) as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "word/document.xml":
                text = payload.decode("utf-8")
                checked = '<w14:checked w14:val="0"/>'
                if text.count(checked) != 3:
                    raise ValueError("unexpected Elsevier declaration checkbox structure")
                text = text.replace(checked, '<w14:checked w14:val="1"/>', 1)
                text = text.replace("<w:t>☐</w:t>", "<w:t>☒</w:t>", 1)
                payload = text.encode("utf-8")
            elif info.filename == "docProps/core.xml":
                text = payload.decode("utf-8")
                for tag in ("dc:creator", "cp:lastModifiedBy"):
                    start = text.find(f"<{tag}>")
                    end = text.find(f"</{tag}>")
                    if start >= 0 and end >= 0:
                        text = text[: start + len(tag) + 2] + text[end:]
                payload = text.encode("utf-8")
            target.writestr(info, payload)

    with zipfile.ZipFile(output) as result:
        document_xml = result.read("word/document.xml").decode("utf-8")
        if document_xml.count('<w14:checked w14:val="1"/>') != 1:
            raise ValueError("filled declaration must select exactly one option")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--template", type=Path)
    args = parser.parse_args()
    build(args.output, args.template)


if __name__ == "__main__":
    main()
