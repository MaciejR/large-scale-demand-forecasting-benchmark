#!/usr/bin/env python3
"""Check that a v1.12 release directory contains the expected public artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


DEFAULT_RELEASE_DIR = Path("release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair")
PDF_NAME = "demand-forecasting-timesfm-fev-bench-wape-covariance-repair-v1.12.pdf"

REQUIRED_FILES = {
    "COMMIT.txt",
    "CHECKSUMS.txt",
    "README.md",
    f"manuscript/{PDF_NAME}",
    "replication/README.md",
    "replication/REPRODUCING.md",
    "replication/ARTIFACTS.md",
    "replication/CITATION.cff",
    "replication/docs/RELEASE_V1.12.md",
    "replication/paper/latex/main.tex",
    "replication/paper/references.bib",
    "replication/analysis/meta_regression.R",
    "replication/analysis/extraction_schema.csv",
    "replication/analysis/study_characteristics.csv",
    "replication/analysis/risk_of_bias_assessment.csv",
    "replication/analysis/prisma_search_protocol.md",
    "replication/analysis/figures/prisma_flow.pdf",
    "replication/analysis/figures/prisma_flow.png",
    "replication/analysis/figures/table_6_1_primary_model_level_deltas.csv",
    "replication/analysis/figures/table_6_1_primary_best_baseline_metric_summary.csv",
    "replication/analysis/figures/table_6_1_primary_best_baseline_suite_metric_summary.csv",
    "replication/analysis/figures/table_6_1_primary_cr2_suite.txt",
    "replication/analysis/figures/table_6_1_cluster_counts.csv",
    "replication/analysis/figures/source_b_integrity_audit_summary.csv",
    "replication/analysis/figures/source_b_paired_panel_fm_vs_best_baseline.csv",
    "replication/analysis/figures/source_b_paired_panel_logratio_covariance.csv",
    "replication/analysis/figures/source_b_paired_panel_run_ledger.csv",
    "replication/analysis/figures/fev_official_run_manifest.csv",
    "replication/analysis/figures/fev_official_model_coverage.csv",
    "replication/analysis/figures/fev_official_bootstrap_manifest.csv",
    "replication/analysis/figures/fev_prediction_level_wape_summary.csv",
    "replication/analysis/figures/fev_chronos_bolt_paired_wape_covariance.csv",
    "replication/analysis/figures/fev_chronos2_paired_wape_covariance.csv",
    "replication/analysis/figures/fev_tirex_paired_wape_covariance.csv",
    "replication/analysis/figures/fev_timesfm25_paired_wape_covariance.csv",
    "replication/tools/audit_publication_readiness.py",
}

REQUIRED_GLOBS = {
    "replication/paper/latex/section*.tex": 9,
    "replication/paper/latex/appendix_*.tex": 7,
    "replication/tests/test_*.py": 10,
}

FORBIDDEN_GLOBS = {
    "replication/.claude/**",
    "replication/analysis/baseline_results.md",
    "replication/paper/drafts/**",
    "replication/paper/latex/*.aux",
    "replication/paper/latex/*.bbl",
    "replication/paper/latex/*.blg",
    "replication/paper/latex/*.log",
    "replication/paper/latex/*.out",
    "replication/paper/latex/*.spl",
    "replication/paper/latex/*.synctex.gz",
}


def audit_release(root: Path) -> list[str]:
    findings: list[str] = []

    for rel_path in sorted(REQUIRED_FILES):
        if not (root / rel_path).is_file():
            findings.append(f"missing required file: {rel_path}")

    for pattern, minimum in sorted(REQUIRED_GLOBS.items()):
        matches = sorted(root.glob(pattern))
        if len(matches) < minimum:
            findings.append(
                f"required glob {pattern} matched {len(matches)} files, expected at least {minimum}"
            )

    for pattern in sorted(FORBIDDEN_GLOBS):
        matches = sorted(path for path in root.glob(pattern) if path.exists())
        for path in matches:
            findings.append(f"forbidden release artifact: {path.relative_to(root).as_posix()}")

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "release_dir",
        nargs="?",
        default=str(DEFAULT_RELEASE_DIR),
        help="Release directory to audit.",
    )
    args = parser.parse_args(argv)

    root = Path(args.release_dir)
    if not root.is_dir():
        print(f"Release manifest audit failed: {root} is not a directory", file=sys.stderr)
        return 1

    findings = audit_release(root)
    if findings:
        print("Release manifest audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print(f"Release manifest audit passed for {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
