#!/usr/bin/env python3
"""Structurally audit the filled Elsevier declaration-of-interest DOCX."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from xml.etree import ElementTree


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
DC = "http://purl.org/dc/elements/1.1/"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"


def audit(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        with zipfile.ZipFile(path) as package:
            bad = package.testzip()
            if bad:
                findings.append(f"corrupt DOCX member: {bad}")
            document = ElementTree.fromstring(package.read("word/document.xml"))
            core = ElementTree.fromstring(package.read("docProps/core.xml"))
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        return [f"invalid declaration DOCX: {exc}"]

    selected_paragraphs: list[str] = []
    unselected_count = 0
    for paragraph in document.iter(f"{{{W}}}p"):
        for checkbox in paragraph.iter(f"{{{W14}}}checkbox"):
            checked = checkbox.find(f"{{{W14}}}checked")
            value = checked.get(f"{{{W14}}}val", "0") if checked is not None else "0"
            if value in {"1", "true", "on"}:
                selected_paragraphs.append("".join(paragraph.itertext()))
            else:
                unselected_count += 1
    if len(selected_paragraphs) != 1:
        findings.append("declaration must select exactly one checkbox")
    if unselected_count != 2:
        findings.append("declaration must leave exactly two checkboxes unselected")
    required = "no known competing financial interests or personal relationships"
    if len(selected_paragraphs) == 1 and required not in selected_paragraphs[0].lower():
        findings.append("selected checkbox is not the no-known-interests statement")
    creator = core.find(f"{{{DC}}}creator")
    modified_by = core.find(f"{{{CP}}}lastModifiedBy")
    if creator is not None and (creator.text or "").strip():
        findings.append("DOCX creator metadata is not empty")
    if modified_by is not None and (modified_by.text or "").strip():
        findings.append("DOCX lastModifiedBy metadata is not empty")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    args = parser.parse_args()
    findings = audit(args.docx)
    if findings:
        for finding in findings:
            print(finding)
        raise SystemExit(1)
    print(f"Declaration DOCX structural audit passed: {args.docx}")


if __name__ == "__main__":
    main()
