#!/usr/bin/env python3
"""Export MLflow runs from the local sweep to a CSV that
`analysis/meta_regression.R` can `bind_rows` onto Source A.

Columns mirror `analysis/extraction_schema.csv` so the R loader can parse
both files under the same schema. Extra columns (runtime_sec, cost_usd,
co2_kg) are appended for the §6.5 Pareto figures — they are ignored by
the primary meta-regression but picked up by `pareto_plot()`.

Usage:
    python tools/export_mlflow_to_csv.py \
        --mlflow-uri file:./mlruns \
        --experiment meta-analysis-gap-filling \
        --out benchmark/results/local_fm_sweep.csv
"""

import argparse
import os
from pathlib import Path

import mlflow
import pandas as pd


# Maps the dataset value logged by run_gap_filling.py to the canonical
# name used in extraction_schema.csv (so normalize_dataset() in R
# collapses both sources into the same bucket).
DATASET_NORMALIZATION = {
    "m5": "M5",
    "favorita": "Favorita",
    "rohlik": "Rohlik v2",
}


def export(mlflow_uri: str, experiment_name: str, out_path: Path) -> int:
    mlflow.set_tracking_uri(mlflow_uri)
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise SystemExit(f"MLflow experiment '{experiment_name}' not found at {mlflow_uri}")

    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="attributes.status = 'FINISHED'",
        output_format="pandas",
    )
    if runs.empty:
        print(f"No finished runs in experiment {experiment_name}.")
        return 0

    # Keep only nested leaf runs (those with a model param). The outer
    # per-dataset wrapper run logs no model.
    if "params.model" not in runs.columns:
        print("No runs with params.model found — nothing to export.")
        return 0
    leaf = runs[runs["params.model"].notna()].copy()

    # Earlier sweep invocations may have left stale runs with the same
    # (model, dataset, horizon) key. Keep only the most recent one so
    # Source B never double-counts the same cell.
    leaf = leaf.sort_values("start_time", ascending=False)
    leaf = leaf.drop_duplicates(
        subset=["params.model", "params.dataset", "params.horizon"],
        keep="first",
    )

    leaf["dataset_canonical"] = leaf["params.dataset"].map(DATASET_NORMALIZATION)
    unknown = leaf[leaf["dataset_canonical"].isna()]
    if not unknown.empty:
        print(f"WARNING: {len(unknown)} runs with unknown dataset(s): "
              f"{sorted(unknown['params.dataset'].unique())}")
        leaf = leaf[leaf["dataset_canonical"].notna()]

    out = pd.DataFrame({
        "paper_id": "LOCAL_" + leaf["params.model"] + "_" + leaf["params.dataset"]
                      + "_h" + leaf["params.horizon"],
        "authors": "own_source_b",
        "year": 2026,
        "title": "Source B — local MPS sweep",
        "venue": "meta-analysis-internal",
        "dataset": leaf["dataset_canonical"],
        "dataset_variant": "",
        "n_series": leaf.get("metrics.WAPE_n_valid", leaf["params.n_series"]).fillna(
            leaf["params.n_series"]
        ),
        "series_length_median": "",
        "frequency": "D",
        "has_covariates": "No",
        "model_name": leaf["params.model"],
        "model_family": "foundation",
        "zero_shot": "Yes",
        "fine_tuned": "No",
        "horizon": leaf["params.horizon"],
        "eval_method": "rolling_origin",
        "metric_name": "WAPE",
        "metric_value": leaf["metrics.WAPE_mean"].round(4).astype(str),
        "runtime_reported": leaf["metrics.runtime_sec"].round(1).astype(str),
        "gpu_hours": "",
        "hardware": leaf["tags.hardware"].fillna("M_SERIES_MAC"),
        "notes": "Source B local sweep; univariate; marginal electricity cost bucket M_SERIES_MAC",
        "runtime_sec": leaf["metrics.runtime_sec"],
        "cost_usd": leaf["metrics.cost_usd"],
        "co2_kg": leaf["metrics.co2_kg"],
    })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out)} rows to {out_path}")
    return len(out)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mlflow-uri", default="file:./mlruns")
    p.add_argument("--experiment", default="meta-analysis-gap-filling")
    p.add_argument("--out", type=Path,
                   default=Path("benchmark/results/local_fm_sweep.csv"))
    args = p.parse_args()
    export(args.mlflow_uri, args.experiment, args.out)


if __name__ == "__main__":
    main()
