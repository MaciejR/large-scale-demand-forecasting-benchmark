#!/usr/bin/env python3
"""Audit PRISMA flow counts across generator, manuscript, and protocol files."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "queries": 25,
    "records_identified": 150,
    "duplicates_removed": 30,
    "after_dedup": 120,
    "screened": 120,
    "excluded_screening": 50,
    "fulltext_assessed": 70,
    "excluded_fulltext": 38,
    "source_a_included": 32,
    "source_b_blocks": 7,
    "extraction_rows": 802,
    "category_a": 17,
    "category_b": 4,
    "category_c": 8,
    "category_d": 3,
}


def read(path: str) -> str:
    return (ROOT / path).read_text()


def require(pattern: str, text: str, label: str) -> None:
    if not re.search(pattern, text, re.MULTILINE):
        raise AssertionError(f"Missing or mismatched PRISMA count: {label}")


def load_prisma_module():
    path = ROOT / "analysis" / "prisma_flow_diagram.py"
    spec = importlib.util.spec_from_file_location("prisma_flow_diagram", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load analysis/prisma_flow_diagram.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_generator() -> None:
    module = load_prisma_module()
    checks = {
        "queries": module.N_QUERIES,
        "records_identified": module.N_DB_RECORDS,
        "duplicates_removed": module.N_DUPLICATES,
        "after_dedup": module.N_AFTER_DEDUP,
        "screened": module.N_SCREENED,
        "excluded_screening": module.N_EXCLUDED_SCREENING,
        "fulltext_assessed": module.N_FULLTEXT_ASSESSED,
        "excluded_fulltext": module.N_EXCLUDED_FULLTEXT,
        "source_a_included": module.N_INCLUDED_EXTERNAL,
        "source_b_blocks": module.N_OWN_EXPERIMENTS,
        "extraction_rows": int(module.N_EXTRACTION_ROWS_LABEL),
        "category_a": module.N_CAT_A,
        "category_b": module.N_CAT_B,
        "category_c": module.N_CAT_C,
        "category_d": module.N_CAT_D,
    }
    for key, value in checks.items():
        if value != EXPECTED[key]:
            raise AssertionError(
                f"analysis/prisma_flow_diagram.py {key}={value}, expected {EXPECTED[key]}"
            )


def audit_manuscript() -> None:
    section4 = read("paper/latex/section4.tex")
    appendix_b = read("paper/latex/appendix_b.tex")

    section4_patterns = {
        "records_identified": rf"Records identified\s*&\s*{EXPECTED['records_identified']}\b",
        "duplicates_removed": rf"Duplicates removed\s*&\s*{EXPECTED['duplicates_removed']}\b",
        "screened": rf"Records screened \(title/abstract\)\s*&\s*{EXPECTED['screened']}\b",
        "excluded_screening": rf"Excluded at screening\s*&\s*{EXPECTED['excluded_screening']}\b",
        "fulltext_assessed": rf"Full-text assessed\s*&\s*{EXPECTED['fulltext_assessed']}\b",
        "excluded_fulltext": rf"Excluded at full-text\s*&\s*{EXPECTED['excluded_fulltext']}\b",
        "source_a_included": rf"Source~A studies included\s*&\s*{EXPECTED['source_a_included']}\b",
        "source_b_blocks": rf"Source~B experiment blocks\s*&\s*{EXPECTED['source_b_blocks']}\b",
        "extraction_rows": rf"Extraction schema rows\s*&\s*{EXPECTED['extraction_rows']}\b",
    }
    for label, pattern in section4_patterns.items():
        require(pattern, section4, f"section4 {label}")

    appendix_patterns = {
        "queries": rf"Total auditable query families:\s*{EXPECTED['queries']}\b",
        "records_identified": rf"Records identified through database/web searching:\s*{EXPECTED['records_identified']}\b",
        "duplicates_removed": rf"Duplicates removed:\s*{EXPECTED['duplicates_removed']}\b",
        "after_dedup": rf"Records after deduplication:\s*{EXPECTED['after_dedup']}\b",
        "screened": rf"Titles/abstracts screened:\s*{EXPECTED['screened']}\b",
        "excluded_screening": rf"Records excluded .*:\s*{EXPECTED['excluded_screening']}\b",
        "fulltext_assessed": rf"Full-text articles assessed for eligibility:\s*{EXPECTED['fulltext_assessed']}\b",
        "excluded_fulltext": rf"Full-text articles excluded:\s*{EXPECTED['excluded_fulltext']}\b",
        "source_a_included": rf"Source A external studies included:\s*{EXPECTED['source_a_included']}\b",
        "source_b_blocks": rf"Source B experiment blocks:\s*{EXPECTED['source_b_blocks']}\b",
    }
    for label, pattern in appendix_patterns.items():
        require(pattern, appendix_b, f"appendix_b {label}")


def audit_protocol() -> None:
    protocol = read("analysis/prisma_search_protocol.md")
    protocol_patterns = {
        "queries": rf"Records identified through database/web searching:\s*{EXPECTED['records_identified']}\s*\({EXPECTED['queries']} auditable query families\)",
        "duplicates_removed": rf"Duplicates removed:\s*{EXPECTED['duplicates_removed']}\b",
        "after_dedup": rf"Records after deduplication:\s*{EXPECTED['after_dedup']}\b",
        "screened": rf"Titles/abstracts screened:\s*{EXPECTED['screened']}\b",
        "excluded_screening": rf"Records excluded .*:\s*{EXPECTED['excluded_screening']}\b",
        "fulltext_assessed": rf"Full-text articles assessed for eligibility:\s*{EXPECTED['fulltext_assessed']}\b",
        "excluded_fulltext": rf"Full-text articles excluded:\s*{EXPECTED['excluded_fulltext']}\b",
        "source_a_included": rf"Source A external studies included:\s*{EXPECTED['source_a_included']}\b",
    }
    for label, pattern in protocol_patterns.items():
        require(pattern, protocol, f"protocol {label}")


def audit_invariants() -> None:
    if EXPECTED["records_identified"] - EXPECTED["duplicates_removed"] != EXPECTED["after_dedup"]:
        raise AssertionError("PRISMA deduplication arithmetic failed")
    if EXPECTED["screened"] - EXPECTED["excluded_screening"] != EXPECTED["fulltext_assessed"]:
        raise AssertionError("PRISMA screening arithmetic failed")
    if EXPECTED["fulltext_assessed"] - EXPECTED["excluded_fulltext"] != EXPECTED["source_a_included"]:
        raise AssertionError("PRISMA inclusion arithmetic failed")
    category_total = (
        EXPECTED["category_a"]
        + EXPECTED["category_b"]
        + EXPECTED["category_c"]
        + EXPECTED["category_d"]
    )
    if category_total != EXPECTED["source_a_included"]:
        raise AssertionError("PRISMA category breakdown does not sum to included Source A studies")


def audit_forbidden_terms() -> None:
    for rel_path in [
        "paper/latex/section4.tex",
        "paper/latex/appendix_b.tex",
        "analysis/prisma_search_protocol.md",
        "analysis/prisma_flow_diagram.py",
    ]:
        text = read(rel_path)
        for forbidden in ["30+ queries", "~250", "approximately 250"]:
            if forbidden in text:
                raise AssertionError(f"Forbidden stale PRISMA wording in {rel_path}: {forbidden}")


def main() -> int:
    try:
        audit_generator()
        audit_manuscript()
        audit_protocol()
        audit_invariants()
        audit_forbidden_terms()
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        "PRISMA count audit passed: "
        f"{EXPECTED['records_identified']} identified, "
        f"{EXPECTED['after_dedup']} screened, "
        f"{EXPECTED['source_a_included']} Source A studies, "
        f"{EXPECTED['queries']} auditable query families."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
