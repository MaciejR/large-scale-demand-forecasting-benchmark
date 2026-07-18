#!/usr/bin/env python3
"""Audit Source B cell coverage, sample matching, and cost consistency.

The repaired manuscript uses these outputs to separate Source B descriptive
evidence from the primary Source A exploratory reanalysis.  The key issue is
not whether rows exist, but whether FM and baseline rows are evaluated on the
same series/workload with paired uncertainty.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "analysis" / "figures"
LOCAL_PATH = ROOT / "benchmark" / "results" / "local_fm_sweep.csv"
BOOTSTRAP_PATH = FIG_DIR / "table_bootstrap_se.csv"
DIRECT_SCALED_PATH = ROOT / "benchmark" / "results" / "direct_scaled_favorita.csv"
COST_BASIS_NOTE = (
    "descriptive legacy Source B accounting; mixes MacBook marginal electricity, "
    "Azure job-level charges, and unequal workloads"
)
COST_AUDIT_STATUS = "not_reconciled_single_ledger"


EXPECTED_MODELS = {
    "chronos2",
    "chronos_bolt_tiny",
    "moirai2",
    "timesfm25",
    "tirex",
    "lightgbm_cov",
    "lightgbm_direct",
    "seasonal_naive",
}
FM_MODELS = {
    "chronos2",
    "chronos_bolt_tiny",
    "moirai2",
    "timesfm25",
    "tirex",
}
DECLARED_DATASET_CAPS = {
    "Favorita": 30000,
    "M5": 30490,
    "Rohlik": 5390,
}


def load_local() -> pd.DataFrame:
    df = pd.read_csv(LOCAL_PATH)
    df["dataset_key"] = df["dataset"].str.lower()
    df["model_name"] = df["model_name"].astype(str)
    df["horizon"] = df["horizon"].astype(int)
    df["n_series"] = pd.to_numeric(df["n_series"], errors="coerce")
    df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")
    df["runtime_sec"] = pd.to_numeric(df["runtime_sec"], errors="coerce")
    df["cost_usd"] = pd.to_numeric(df["cost_usd"], errors="coerce")
    df["co2_kg"] = pd.to_numeric(df["co2_kg"], errors="coerce")
    return df


def write_cell_coverage(local: pd.DataFrame) -> None:
    coverage = (
        local.groupby(["dataset", "horizon"], dropna=False)["model_name"]
        .agg(lambda s: ";".join(sorted(s)))
        .reset_index(name="models_present")
    )
    coverage["n_models_present"] = coverage["models_present"].str.count(";") + 1
    coverage["missing_models"] = coverage["models_present"].apply(
        lambda s: ";".join(sorted(EXPECTED_MODELS - set(s.split(";"))))
    )
    coverage["all_8_models_present"] = coverage["missing_models"].eq("")
    coverage.to_csv(FIG_DIR / "source_b_cell_coverage.csv", index=False)


def write_n_series_matrix(local: pd.DataFrame) -> pd.DataFrame:
    matrix = (
        local.pivot_table(
            index=["dataset", "horizon"],
            columns="model_name",
            values="n_series",
            aggfunc="first",
        )
        .reset_index()
        .sort_values(["dataset", "horizon"])
    )
    matrix.to_csv(FIG_DIR / "source_b_n_series_matrix.csv", index=False)

    long = local[["dataset", "horizon", "model_name", "n_series", "metric_value"]]
    long.to_csv(FIG_DIR / "source_b_wape_and_n_series_long.csv", index=False)
    return matrix


def write_n_series_semantics_audit(local: pd.DataFrame) -> None:
    """Document what the recorded n_series field can and cannot prove."""
    rows = []
    for _, row in local.sort_values(["dataset", "horizon", "model_name"]).iterrows():
        dataset = row["dataset"]
        cap = DECLARED_DATASET_CAPS.get(dataset)
        n_series = row["n_series"]
        exceeds_cap = bool(pd.notna(n_series) and cap is not None and n_series > cap)
        if exceeds_cap:
            plausible = "not_unique_series_ids"
            note = (
                "Recorded n_series exceeds the declared dataset cap; treat as "
                "a workload or observation count until row-level IDs are recovered."
            )
        elif pd.notna(n_series) and n_series <= 150:
            plausible = "small_sample_or_valid_series_count"
            note = (
                "Recorded count is compatible with the legacy small-sample "
                "bootstrap workload, but row-level IDs are not available here."
            )
        else:
            plausible = "recorded_workload_count"
            note = (
                "Recorded count may be unique series, valid WAPE series, or "
                "another workload denominator; the saved aggregate file does not "
                "store row-level series IDs."
            )
        rows.append(
            {
                "dataset": dataset,
                "horizon": row["horizon"],
                "model_name": row["model_name"],
                "recorded_n_series": n_series,
                "declared_dataset_cap_or_reference": cap,
                "exceeds_declared_cap": exceeds_cap,
                "plausible_count_type": plausible,
                "interpretation_note": note,
            }
        )
    pd.DataFrame(rows).to_csv(
        FIG_DIR / "source_b_workload_semantics_audit.csv", index=False
    )


def write_bootstrap_audit() -> None:
    bse = pd.read_csv(BOOTSTRAP_PATH)
    bse["model"] = bse["model"].astype(str)
    observed_fms = set(bse["model"])
    bootstrap_summary = pd.DataFrame(
        [
            {
                "expected_fm_cells": len(FM_MODELS) * 3 * 3,
                "observed_bootstrap_cells": len(bse),
                "expected_fm_models": ";".join(sorted(FM_MODELS)),
                "observed_bootstrap_models": ";".join(sorted(observed_fms)),
                "missing_bootstrap_models": ";".join(sorted(FM_MODELS - observed_fms)),
                "min_n_valid": int(bse["n_valid"].min()),
                "max_n_valid": int(bse["n_valid"].max()),
                "median_bootstrap_se": float(bse["bootstrap_se"].median()),
                "max_bootstrap_se": float(bse["bootstrap_se"].max()),
            }
        ]
    )
    bootstrap_summary.to_csv(FIG_DIR / "source_b_bootstrap_audit.csv", index=False)


def write_cost_audit(local: pd.DataFrame) -> None:
    by_dataset = (
        local.groupby(["dataset", "model_family"], dropna=False)
        .agg(
            rows=("model_name", "count"),
            runtime_sec=("runtime_sec", "sum"),
            cost_usd=("cost_usd", "sum"),
            co2_kg=("co2_kg", "sum"),
            min_n_series=("n_series", "min"),
            max_n_series=("n_series", "max"),
        )
        .reset_index()
    )
    by_dataset["cost_basis_note"] = COST_BASIS_NOTE
    by_dataset["audit_status"] = COST_AUDIT_STATUS
    by_dataset.to_csv(FIG_DIR / "source_b_cost_by_dataset_family.csv", index=False)

    total = pd.DataFrame(
        [
            {
                "rows": len(local),
                "runtime_sec": local["runtime_sec"].sum(),
                "runtime_hours": local["runtime_sec"].sum() / 3600,
                "cost_usd": local["cost_usd"].sum(),
                "co2_kg": local["co2_kg"].sum(),
                "cost_basis_note": COST_BASIS_NOTE,
                "audit_status": COST_AUDIT_STATUS,
            }
        ]
    )
    total.to_csv(FIG_DIR / "source_b_cost_total.csv", index=False)


def write_direct_scaled_audit(local: pd.DataFrame) -> None:
    if not DIRECT_SCALED_PATH.exists():
        return
    scaled = pd.read_csv(DIRECT_SCALED_PATH)
    scaled["horizon"] = scaled["horizon"].astype(int)
    scaled["metric_value"] = pd.to_numeric(scaled["metric_value"], errors="coerce")
    base_direct = local[
        (local["dataset"].str.lower() == "favorita")
        & (local["model_name"] == "lightgbm_direct")
    ][["horizon", "metric_value", "runtime_sec", "cost_usd"]].rename(
        columns={
            "metric_value": "base_direct_wape",
            "runtime_sec": "base_runtime_sec",
            "cost_usd": "base_cost_usd",
        }
    )
    recursive = local[
        (local["dataset"].str.lower() == "favorita")
        & (local["model_name"] == "lightgbm_cov")
    ][["horizon", "metric_value", "runtime_sec", "cost_usd"]].rename(
        columns={
            "metric_value": "recursive_wape",
            "runtime_sec": "recursive_runtime_sec",
            "cost_usd": "recursive_cost_usd",
        }
    )
    audit = scaled.merge(base_direct, on="horizon", how="left")
    audit = audit.merge(recursive, on="horizon", how="left")
    audit["wape_delta_scaled_minus_base"] = (
        audit["metric_value"] - audit["base_direct_wape"]
    )
    audit["wape_delta_scaled_minus_recursive"] = (
        audit["metric_value"] - audit["recursive_wape"]
    )
    audit["same_tree_count_as_base_h7"] = (
        (audit["horizon"] == 7) & (audit["n_estimators_per_head"] == 300)
    )
    audit["scaled_more_accurate_than_recursive"] = (
        audit["metric_value"] < audit["recursive_wape"]
    )
    audit["integrity_flag"] = audit.apply(
        lambda row: (
            "same_nominal_tree_count_but_wape_changed"
            if row["same_tree_count_as_base_h7"]
            and abs(row["wape_delta_scaled_minus_base"]) > 1e-6
            else "not_interpretable_until_protocol_diff_explained"
        ),
        axis=1,
    )
    audit[
        [
            "horizon",
            "n_estimators_per_head",
            "metric_value",
            "base_direct_wape",
            "recursive_wape",
            "wape_delta_scaled_minus_base",
            "wape_delta_scaled_minus_recursive",
            "same_tree_count_as_base_h7",
            "scaled_more_accurate_than_recursive",
            "integrity_flag",
            "runtime_sec",
            "base_runtime_sec",
            "recursive_runtime_sec",
            "cost_usd",
            "base_cost_usd",
            "recursive_cost_usd",
        ]
    ].to_csv(FIG_DIR / "source_b_direct_scaled_audit.csv", index=False)


def write_table8_bootstrap_reconciliation(local: pd.DataFrame) -> None:
    if not BOOTSTRAP_PATH.exists():
        return
    bse = pd.read_csv(BOOTSTRAP_PATH)
    bse["dataset"] = bse["dataset"].str.capitalize()
    bse.loc[bse["dataset"].str.lower() == "m5", "dataset"] = "M5"
    bse["model_name"] = bse["model"].astype(str)
    bse["horizon"] = bse["horizon"].astype(int)
    fm_saved = local[local["model_name"].isin(FM_MODELS)][
        ["dataset", "horizon", "model_name", "metric_value", "n_series"]
    ].rename(
        columns={
            "metric_value": "unmatched_saved_sweep_wape",
            "n_series": "unmatched_saved_sweep_n_series",
        }
    )
    legacy = bse[
        ["dataset", "horizon", "model_name", "n_valid", "wape_mean", "bootstrap_se"]
    ].rename(
        columns={
            "n_valid": "legacy_100_series_n_valid",
            "wape_mean": "legacy_100_series_bootstrap_wape",
            "bootstrap_se": "legacy_100_series_bootstrap_se",
        }
    )
    reconciled = fm_saved.merge(
        legacy, on=["dataset", "horizon", "model_name"], how="outer"
    )
    reconciled["wape_delta_saved_minus_legacy"] = (
        reconciled["unmatched_saved_sweep_wape"]
        - reconciled["legacy_100_series_bootstrap_wape"]
    )
    reconciled["workload_note"] = (
        "Table 8 saved sweep and Appendix C legacy bootstrap are different "
        "workloads; deltas are integrity diagnostics, not model effects."
    )
    reconciled.sort_values(["dataset", "horizon", "model_name"]).to_csv(
        FIG_DIR / "source_b_table8_vs_legacy_bootstrap_reconciliation.csv",
        index=False,
    )


def write_cost_consistency_audit() -> None:
    """Record the manuscript-level cost mismatch that must be resolved."""
    rows = [
        {
            "scope": "M5 total",
            "detail_tables_usd": 0.877,
            "summary_table_usd": 0.810,
            "difference_usd": 0.810 - 0.877,
            "status": "mismatch_requires_single_ledger",
        },
        {
            "scope": "Rohlik total",
            "detail_tables_usd": 0.1098,
            "summary_table_usd": 0.120,
            "difference_usd": 0.120 - 0.1098,
            "status": "mismatch_requires_single_ledger",
        },
        {
            "scope": "Favorita total",
            "detail_tables_usd": 0.7765,
            "summary_table_usd": 1.119,
            "difference_usd": 1.119 - 0.7765,
            "status": "mismatch_requires_single_ledger",
        },
        {
            "scope": "Favorita direct",
            "detail_tables_usd": 0.6870,
            "summary_table_usd": 1.030,
            "difference_usd": 1.030 - 0.6870,
            "status": "mismatch_requires_single_ledger",
        },
        {
            "scope": "M5 seasonal naive",
            "detail_tables_usd": 0.059,
            "summary_table_usd": 0.146,
            "difference_usd": 0.146 - 0.059,
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
    audit = pd.DataFrame(rows)
    audit.to_csv(FIG_DIR / "source_b_cost_consistency_audit.csv", index=False)
    write_cost_consistency_latex(audit)


def latex_escape(value: object) -> str:
    text = str(value)
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
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def format_decimal(value: object, places: str = "0.001") -> str:
    return str(Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def format_signed_decimal(value: object) -> str:
    number = Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    sign = "+" if number >= 0 else "-"
    return f"{sign}{abs(number)}"


def write_cost_consistency_latex(audit: pd.DataFrame) -> None:
    """Write the Appendix G cost audit table from the CSV source."""
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Baseline cost consistency audit.  Differences are too large to",
        r"treat as rounding; a single run ledger is required before cost claims are",
        r"promoted from descriptive to inferential.}",
        r"\label{tab:t56}",
        r"\small",
        r"\begin{tabularx}{\textwidth}{lrrrX}",
        r"\toprule",
        r"Scope & Detail tables (USD) & Summary table (USD) & Difference & Status \\",
        r"\midrule",
    ]
    for _, row in audit.iterrows():
        diff = float(row["difference_usd"])
        status = str(row["status"]).replace("_", " ")
        lines.append(
            f"{latex_escape(row['scope'])} & "
            f"{format_decimal(row['detail_tables_usd'])} & "
            f"{format_decimal(row['summary_table_usd'])} & "
            f"${format_signed_decimal(diff)}$ & "
            f"{latex_escape(status)} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\end{table}",
        ]
    )
    (FIG_DIR / "source_b_cost_consistency_audit.tex").write_text(
        "\n".join(lines) + "\n"
    )


def write_integrity_flags(local: pd.DataFrame) -> None:
    rows = []
    for (dataset, horizon), group in local.groupby(["dataset", "horizon"]):
        n_values = sorted(group["n_series"].dropna().unique())
        models = set(group["model_name"])
        rows.append(
            {
                "dataset": dataset,
                "horizon": horizon,
                "models_present": len(models),
                "all_8_models_present": EXPECTED_MODELS.issubset(models),
                "min_n_series": min(n_values) if n_values else None,
                "max_n_series": max(n_values) if n_values else None,
                "n_series_unique_values": len(n_values),
                "n_series_matched_across_models": len(n_values) == 1,
                "source_b_pairwise_matched": False,
                "reason": (
                    "n_series differs across models; row-level series identifiers "
                    "and paired prediction errors are not available for all models"
                ),
            }
        )
    pd.DataFrame(rows).to_csv(FIG_DIR / "source_b_integrity_flags.csv", index=False)


def write_integrity_summary(local: pd.DataFrame) -> None:
    """Write one machine-readable status table for Source B audit gates."""
    integrity_flags = pd.read_csv(FIG_DIR / "source_b_integrity_flags.csv")
    direct_scaled = pd.read_csv(FIG_DIR / "source_b_direct_scaled_audit.csv")
    cost_total = pd.read_csv(FIG_DIR / "source_b_cost_total.csv")
    matched_panel = pd.read_csv(FIG_DIR / "source_b_paired_panel_cell_summary.csv")

    expected_matched_models = {
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
    matched_coverage = matched_panel.groupby(["dataset", "horizon"])["model_name"].agg(
        lambda s: set(s)
    )
    matched_panel_complete = (
        len(matched_panel) == 81
        and len(matched_coverage) == 9
        and all(models == expected_matched_models for models in matched_coverage)
    )
    direct_scaled_h7_flagged = (
        "same_nominal_tree_count_but_wape_changed"
        in set(direct_scaled["integrity_flag"])
    )
    cost_unreconciled = set(cost_total["audit_status"]) == {
        COST_AUDIT_STATUS
    }

    rows = [
        {
            "gate": "legacy_source_b_pairing",
            "status": "failed",
            "evidence_file": "analysis/figures/source_b_integrity_flags.csv",
            "evidence_summary": (
                f"{int((~integrity_flags['n_series_matched_across_models']).sum())} "
                "dataset-horizon cells have unequal recorded n_series values across models"
            ),
            "manuscript_consequence": (
                "legacy Source B remains descriptive and is not pooled into Source A"
            ),
        },
        {
            "gate": "matched_panel_coverage",
            "status": "passed" if matched_panel_complete else "failed",
            "evidence_file": "analysis/figures/source_b_paired_panel_cell_summary.csv",
            "evidence_summary": (
                f"{len(matched_panel)} model-dataset-horizon rows; "
                f"{len(matched_coverage)} dataset-horizon cells"
            ),
            "manuscript_consequence": (
                "matched-panel Source B repair can be reported as local paired evidence"
            ),
        },
        {
            "gate": "legacy_cost_reconciliation",
            "status": "failed" if cost_unreconciled else "passed",
            "evidence_file": "analysis/figures/source_b_cost_total.csv",
            "evidence_summary": cost_total["audit_status"].iloc[0],
            "manuscript_consequence": (
                "legacy Source B costs remain descriptive until one run ledger reconciles tables"
            ),
        },
        {
            "gate": "legacy_direct_scaled_protocol",
            "status": "failed" if direct_scaled_h7_flagged else "passed",
            "evidence_file": "analysis/figures/source_b_direct_scaled_audit.csv",
            "evidence_summary": (
                "h=7 scaled direct has the same nominal 300-tree count as base direct "
                "but a different WAPE"
                if direct_scaled_h7_flagged
                else "no same-tree-count direct_scaled anomaly detected"
            ),
            "manuscript_consequence": (
                "legacy direct_scaled Favorita run remains a rerun target, not ranking evidence"
            ),
        },
        {
            "gate": "source_b_formal_pooling",
            "status": "blocked_by_design",
            "evidence_file": "analysis/figures/source_b_integrity_audit_summary.csv",
            "evidence_summary": (
                "formal pooling requires prediction-level covariance on the target estimand "
                "and reconciled workloads"
            ),
            "manuscript_consequence": (
                "Source B is separated from Source A and used as local sensitivity evidence"
            ),
        },
    ]
    pd.DataFrame(rows).to_csv(
        FIG_DIR / "source_b_integrity_audit_summary.csv", index=False
    )


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    local = load_local()
    write_cell_coverage(local)
    write_n_series_matrix(local)
    write_n_series_semantics_audit(local)
    write_bootstrap_audit()
    write_cost_audit(local)
    write_direct_scaled_audit(local)
    write_table8_bootstrap_reconciliation(local)
    write_cost_consistency_audit()
    write_integrity_flags(local)
    write_integrity_summary(local)
    print("Wrote Source B audit outputs to", FIG_DIR)


if __name__ == "__main__":
    main()
