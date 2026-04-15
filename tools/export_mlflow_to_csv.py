#!/usr/bin/env python3
"""Export MLflow runs from local + Azure sweeps to a CSV that
`analysis/meta_regression.R` can `bind_rows` onto Source A.

Pulls from two tracking backends:
  - Local file store (`file:./mlruns`) — FM cells (chronos, tirex) run
    on the MacBook for §5.4 local sensitivity sweep.
  - Azure ML workspace — ML_TREE baselines (lightgbm_cov, lightgbm_direct)
    and seasonal_naive, run on cc-forecast-batch in `rg-forecast-benchmark`.

Rows from both sources share a single `paper_id = LOCAL_MAC_<dataset>_h<horizon>`,
so the R §6.1 dataset-anchored Δ pass sees FM and ML_TREE as within-paper
pairs and can compute `delta = fm - ml_tree` per cell.

Extra columns (runtime_sec, cost_usd, co2_kg) are appended for the §6.5
Pareto figures — ignored by the primary meta-regression but picked up by
`pareto_plot()`.

Usage:
    python tools/export_mlflow_to_csv.py \
        --out benchmark/results/local_fm_sweep.csv
"""

import argparse
from pathlib import Path
from typing import Optional

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

# Azure ML workspace tracking URI for the meta-analysis experiment. The
# workspace/resource-group/subscription triple is stable across runs so
# the URI is baked in here rather than routed through yet another flag.
AZURE_MLFLOW_URI = (
    "azureml://swedencentral.api.azureml.ms/mlflow/v1.0/"
    "subscriptions/ad0f5d80-04ce-435e-9130-dbf3a540ebd3/"
    "resourceGroups/rg-forecast-benchmark/"
    "providers/Microsoft.MachineLearningServices/"
    "workspaces/mlw-forecast-benchmark"
)

# Model-name → normalized meta-analysis family. Anything not listed is
# dropped with a warning so the exporter never silently mis-classifies.
MODEL_FAMILY = {
    "chronos_bolt_tiny": "foundation",
    "chronos_bolt_small": "foundation",
    "chronos_bolt_base": "foundation",
    "tirex": "foundation",
    "tabpfn_ts": "foundation",
    "timesfm": "foundation",
    "moirai": "foundation",
    "lightgbm_cov": "ml_tree",
    "lightgbm_direct": "ml_tree",
    "lightgbm": "ml_tree",
    "seasonal_naive": "statistical",
    "naive": "statistical",
}

FM_MODELS = {m for m, f in MODEL_FAMILY.items() if f == "foundation"}


def load_leaf_runs(
    mlflow_uri: str,
    experiment_name: str,
    source_label: str,
) -> pd.DataFrame:
    """Return deduped leaf runs from one MLflow backend, tagged with source."""
    mlflow.set_tracking_uri(mlflow_uri)
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        print(f"WARNING: experiment '{experiment_name}' not found at {mlflow_uri}")
        return pd.DataFrame()

    # Don't push the status filter into search_runs — Azure MLflow's
    # server-side filter_string parser rejects `attributes.status =
    # 'FINISHED'` and returns an empty frame. Fetch everything and
    # filter client-side instead.
    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        output_format="pandas",
    )
    if runs.empty:
        print(f"No runs at {source_label}.")
        return runs
    if "status" in runs.columns:
        runs = runs[runs["status"] == "FINISHED"]

    if "params.model" not in runs.columns:
        print(f"No runs with params.model at {source_label} — skipping.")
        return pd.DataFrame()

    leaf = runs[runs["params.model"].notna()].copy()
    leaf["_source_label"] = source_label

    # Earlier sweep invocations may have left stale runs with the same
    # (model, dataset, horizon) key. Keep only the most recent one so
    # Source B never double-counts the same cell.
    leaf = leaf.sort_values("start_time", ascending=False)
    leaf = leaf.drop_duplicates(
        subset=["params.model", "params.dataset", "params.horizon"],
        keep="first",
    )
    print(f"  {source_label}: {len(leaf)} deduped leaf runs")
    return leaf


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Return column `name` or an all-NA series if missing from this backend."""
    if name in df.columns:
        return df[name]
    return pd.Series([pd.NA] * len(df), index=df.index)


def build_rows(leaf: pd.DataFrame) -> pd.DataFrame:
    leaf = leaf.copy()
    leaf["dataset_canonical"] = leaf["params.dataset"].map(DATASET_NORMALIZATION)
    unknown_ds = leaf[leaf["dataset_canonical"].isna()]
    if not unknown_ds.empty:
        print(f"  dropping {len(unknown_ds)} rows with unknown dataset(s): "
              f"{sorted(unknown_ds['params.dataset'].unique())}")
        leaf = leaf[leaf["dataset_canonical"].notna()]

    leaf["family"] = leaf["params.model"].map(MODEL_FAMILY)
    unknown_model = leaf[leaf["family"].isna()]
    if not unknown_model.empty:
        print(f"  dropping {len(unknown_model)} rows with unknown model(s): "
              f"{sorted(unknown_model['params.model'].unique())}")
        leaf = leaf[leaf["family"].notna()]

    if leaf.empty:
        return leaf

    is_fm = leaf["family"] == "foundation"
    zero_shot = is_fm.map({True: "Yes", False: "No"})
    has_cov = leaf["params.model"].eq("lightgbm_cov").map({True: "Yes", False: "No"})

    # Source tag: local Mac sweep vs Azure batch. Drives the hardware
    # column that the §6.5 Pareto figures bucket on.
    is_local = leaf["_source_label"] == "local"
    hardware = is_local.map({True: "M_SERIES_MAC", False: "AZURE_E4DS_V4"})
    notes = is_local.map({
        True: "Source B local sweep; univariate; marginal electricity cost bucket M_SERIES_MAC",
        False: "Source B Azure batch; cc-forecast-batch; list-price AZURE_GENERAL_V4 bucket",
    })

    runtime = _col(leaf, "metrics.runtime_sec")
    cost = _col(leaf, "metrics.cost_usd")
    co2 = _col(leaf, "metrics.co2_kg")
    wape = _col(leaf, "metrics.WAPE_mean")
    n_valid = _col(leaf, "metrics.WAPE_n_valid")
    n_series_param = _col(leaf, "params.n_series")

    out = pd.DataFrame({
        # Shared paper_id across FM and ML_TREE rows for the same cell —
        # this is what unlocks §6.1 paired Δ in the R meta-regression.
        "paper_id": "LOCAL_MAC_" + leaf["params.dataset"]
                      + "_h" + leaf["params.horizon"].astype(str),
        "authors": "own_source_b",
        "year": 2026,
        "title": "Source B — local MPS + Azure batch sweep",
        "venue": "meta-analysis-internal",
        "dataset": leaf["dataset_canonical"].values,
        "dataset_variant": "",
        "n_series": n_valid.fillna(n_series_param).values,
        "series_length_median": "",
        "frequency": "D",
        "has_covariates": has_cov.values,
        "model_name": leaf["params.model"].values,
        "model_family": leaf["family"].values,
        "zero_shot": zero_shot.values,
        "fine_tuned": "No",
        "horizon": leaf["params.horizon"].values,
        "eval_method": "rolling_origin",
        "metric_name": "WAPE",
        "metric_value": wape.round(4).astype(str).values,
        "runtime_reported": runtime.round(1).astype(str).values,
        "gpu_hours": "",
        "hardware": hardware.values,
        "notes": notes.values,
        "runtime_sec": runtime.values,
        "cost_usd": cost.values,
        "co2_kg": co2.values,
    })
    return out


def export(
    out_path: Path,
    local_uri: str,
    azure_uri: Optional[str],
    experiment_name: str,
) -> int:
    print(f"Pulling local MLflow runs from {local_uri}")
    local = load_leaf_runs(local_uri, experiment_name, "local")

    if azure_uri:
        print(f"Pulling Azure MLflow runs from {azure_uri}")
        azure = load_leaf_runs(azure_uri, experiment_name, "azure")
    else:
        azure = pd.DataFrame()

    frames = [f for f in (local, azure) if not f.empty]
    if not frames:
        print("No runs found in any backend.")
        return 0

    combined = pd.concat(frames, ignore_index=True, sort=False)
    out = build_rows(combined)
    if out.empty:
        print("No rows after family/dataset filtering.")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out)} rows to {out_path}")
    print(f"  by family: {out['model_family'].value_counts().to_dict()}")
    return len(out)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local-uri", default="file:./mlruns",
                   help="Local MLflow tracking URI (foundation models)")
    p.add_argument("--azure-uri", default=AZURE_MLFLOW_URI,
                   help="Azure ML workspace MLflow URI (ML_TREE + stats baselines). "
                        "Pass empty string to skip.")
    p.add_argument("--experiment", default="meta-analysis-gap-filling")
    p.add_argument("--out", type=Path,
                   default=Path("benchmark/results/local_fm_sweep.csv"))
    args = p.parse_args()
    export(
        out_path=args.out,
        local_uri=args.local_uri,
        azure_uri=args.azure_uri or None,
        experiment_name=args.experiment,
    )


if __name__ == "__main__":
    main()
