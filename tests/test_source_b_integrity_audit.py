"""Regression tests for Source B integrity-audit artifacts."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "analysis")

import source_b_integrity_audit as audit


def test_cost_consistency_latex_is_generated_from_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "FIG_DIR", tmp_path)
    rows = pd.DataFrame(
        [
            {
                "scope": "Favorita total",
                "detail_tables_usd": 0.7765,
                "summary_table_usd": 1.119,
                "difference_usd": 1.119 - 0.7765,
                "status": "mismatch_requires_single_ledger",
            },
            {
                "scope": "M5 direct",
                "detail_tables_usd": 0.724,
                "summary_table_usd": 0.571,
                "difference_usd": 0.571 - 0.724,
                "status": "mismatch_requires_single_ledger",
            },
        ]
    )

    audit.write_cost_consistency_latex(rows)

    tex = (tmp_path / "source_b_cost_consistency_audit.tex").read_text()
    assert "Favorita total & 0.777 & 1.119 & $+0.343$" in tex
    assert "M5 direct & 0.724 & 0.571 & $-0.153$" in tex
    assert "mismatch requires single ledger" in tex


def test_current_matched_panel_has_complete_nine_model_coverage():
    path = Path("analysis/figures/source_b_paired_panel_cell_summary.csv")
    summary = pd.read_csv(path)
    expected_models = {
        "chronos2",
        "chronos_bolt_tiny",
        "lightgbm_cov",
        "lightgbm_direct",
        "lightgbm_direct_scaled",
        "moirai2",
        "seasonal_naive",
        "timesfm25",
        "tirex",
    }

    assert len(summary) == 81
    assert not summary.duplicated(["dataset", "horizon", "model_name"]).any()
    assert set(summary["model_name"]) == expected_models

    coverage = summary.groupby(["dataset", "horizon"])["model_name"].agg(set)
    assert len(coverage) == 9
    assert all(models == expected_models for models in coverage)
