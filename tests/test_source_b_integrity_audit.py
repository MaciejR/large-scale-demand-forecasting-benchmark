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


def test_cost_audit_outputs_are_explicitly_descriptive(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "FIG_DIR", tmp_path)
    local = pd.DataFrame(
        [
            {
                "dataset": "M5",
                "model_family": "foundation",
                "model_name": "chronos2",
                "runtime_sec": 10.0,
                "cost_usd": 0.02,
                "co2_kg": 0.001,
                "n_series": 100,
            },
            {
                "dataset": "M5",
                "model_family": "ml_tree",
                "model_name": "lightgbm_cov",
                "runtime_sec": 20.0,
                "cost_usd": 0.03,
                "co2_kg": 0.002,
                "n_series": 1000,
            },
        ]
    )

    audit.write_cost_audit(local)

    total = pd.read_csv(tmp_path / "source_b_cost_total.csv")
    by_dataset = pd.read_csv(tmp_path / "source_b_cost_by_dataset_family.csv")

    for frame in (total, by_dataset):
        assert "cost_basis_note" in frame.columns
        assert "audit_status" in frame.columns
        assert set(frame["audit_status"]) == {"not_reconciled_single_ledger"}
        assert frame["cost_basis_note"].str.contains("descriptive legacy Source B").all()


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


def test_risk_of_bias_assessment_is_study_level():
    risk = pd.read_csv("analysis/risk_of_bias_assessment.csv")
    studies = pd.read_csv("analysis/study_characteristics.csv")
    required_columns = {
        "study_id",
        "baseline_quality",
        "matched_protocol",
        "leakage_risk",
        "selective_reporting_risk",
        "raw_predictions_available",
        "code_available",
        "independence_note",
        "overall_risk",
    }

    assert required_columns.issubset(risk.columns)
    assert risk["study_id"].is_unique
    assert set(risk["study_id"]) == set(studies["study_id"])
    assert not risk[list(required_columns)].isna().any().any()


def test_source_b_integrity_summary_records_audit_gates():
    summary_path = Path("analysis/figures/source_b_integrity_audit_summary.csv")
    assert summary_path.exists()

    summary = pd.read_csv(summary_path)
    expected_gates = {
        "legacy_source_b_pairing": "failed",
        "matched_panel_coverage": "passed",
        "legacy_cost_reconciliation": "failed",
        "legacy_direct_scaled_protocol": "failed",
        "source_b_formal_pooling": "blocked_by_design",
    }

    assert set(summary["gate"]) == set(expected_gates)
    actual = dict(zip(summary["gate"], summary["status"]))
    assert actual == expected_gates
    assert summary["evidence_file"].str.startswith("analysis/figures/").all()
    assert summary["manuscript_consequence"].str.len().min() > 20
