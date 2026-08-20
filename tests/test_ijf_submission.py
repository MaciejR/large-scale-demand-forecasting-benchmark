from pathlib import Path
import importlib.util
import os
import re
import subprocess
import sys
import zipfile
from xml.etree import ElementTree

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from anonymize_ijf_supplement import audit_tree, sanitize_tree
from audit_ijf_declaration import audit as audit_declaration
from create_deterministic_zip import create_zip

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_ijf_anonymity", ROOT / "tools/audit_ijf_anonymity.py"
)
AUDIT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT_MODULE)


def test_abstract_is_within_ijf_word_limit():
    source = (ROOT / "paper/latex/main.tex").read_text()
    abstract = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}", source, re.DOTALL
    ).group(1)
    plain = re.sub(r"\\[A-Za-z]+(?:\{\})?", " metric ", abstract)
    plain = re.sub(r"[{}~]", " ", plain)
    words = re.findall(r"\b[\w-]+\b", plain)
    assert 100 <= len(words) <= 150


def test_highlights_are_concise():
    lines = (ROOT / "paper/submission/highlights.txt").read_text().splitlines()
    highlights = [line[2:] for line in lines if line.startswith("- ")]
    assert 3 <= len(highlights) <= 5
    assert all(len(item) <= 85 for item in highlights)


def test_anonymous_wrapper_and_conditional_identity_blocks_exist():
    wrapper = (ROOT / "paper/latex/main_anonymized.tex").read_text()
    source = (ROOT / "paper/latex/main.tex").read_text()
    assert "\\def\\anonymoussubmission{1}" in wrapper
    assert source.count("\\ifdefined\\anonymoussubmission") >= 5


def test_built_anonymous_pdf_has_no_identity_leaks():
    pdf = ROOT / "paper/latex/main_anonymized.pdf"
    assert pdf.is_file()
    assert AUDIT_MODULE.audit(pdf) == []
    first_page = subprocess.check_output(
        ["pdftotext", "-f", "1", "-l", "1", str(pdf), "-"], text=True
    )
    assert "When Do Foundation Models Pay Off" in first_page
    assert "Anonymous manuscript" in first_page


def test_declaration_docx_selects_only_no_conflicts_option():
    path = ROOT / "paper/submission/declaration_of_interests.docx"
    assert audit_declaration(path) == []


def test_declaration_rejects_a_different_selected_option(tmp_path):
    source = ROOT / "paper/submission/declaration_of_interests.docx"
    destination = tmp_path / "wrong-option.docx"
    w14 = "http://schemas.microsoft.com/office/word/2010/wordml"
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, "w") as changed:
        document = ElementTree.fromstring(original.read("word/document.xml"))
        checked = list(document.iter(f"{{{w14}}}checked"))
        checked[0].set(f"{{{w14}}}val", "0")
        checked[1].set(f"{{{w14}}}val", "1")
        for item in original.infolist():
            content = (
                ElementTree.tostring(document, encoding="utf-8", xml_declaration=True)
                if item.filename == "word/document.xml"
                else original.read(item)
            )
            changed.writestr(item, content)
    assert "selected checkbox is not the no-known-interests statement" in audit_declaration(destination)


def test_anonymous_supplement_sanitizer_removes_identity(tmp_path):
    sample = tmp_path / "sample.txt"
    sample.write_text(
        "Maciej Rubczynski /" + "Users/maciej/private "
        "10.5281/zenodo.21338004 large-scale-demand-forecasting-benchmark"
    )
    sanitize_tree(tmp_path)
    assert audit_tree(tmp_path) != []  # local paths are rejected, not rewritten
    sample.write_text("Anonymous review supplement")
    assert audit_tree(tmp_path) == []


def test_deterministic_zip_bytes_match(tmp_path):
    source = tmp_path / "package"
    source.mkdir()
    (source / "b.txt").write_text("b")
    (source / "a.txt").write_text("a")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    create_zip(source, first)
    create_zip(source, second)
    assert first.read_bytes() == second.read_bytes()


def test_deterministic_zip_rejects_symlinks(tmp_path):
    source = tmp_path / "package"
    source.mkdir()
    target = tmp_path / "private.txt"
    target.write_text("private")
    (source / "escape.txt").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        create_zip(source, tmp_path / "output.zip")


def test_anonymous_audit_rejects_symlinks(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("safe")
    (tmp_path / "alias.txt").symlink_to(target)
    assert any("forbidden symlink" in item for item in audit_tree(tmp_path))


def test_anonymous_audit_inspects_parquet_metadata(tmp_path):
    pa = pytest.importorskip("pyarrow")
    parquet = pytest.importorskip("pyarrow.parquet")
    table = pa.table({"value": [1]}).replace_schema_metadata({b"author": b"Maciej Rubczynski"})
    parquet.write_table(table, tmp_path / "sample.parquet")
    assert any("matches" in item for item in audit_tree(tmp_path))


def test_private_title_page_refuses_to_overwrite_without_address(tmp_path):
    output = tmp_path / "title-page.pdf"
    output.write_bytes(b"existing-private-pdf")
    environment = os.environ.copy()
    environment.pop("IJF_POSTAL_ADDRESS", None)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_private_title_page.py"),
            "--output",
            str(output),
        ],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert output.read_bytes() == b"existing-private-pdf"
