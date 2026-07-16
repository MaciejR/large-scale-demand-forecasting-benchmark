#!/usr/bin/env python3
"""Paired bootstrap report for fev-bench prediction-level artifacts.

This script consumes outputs from benchmark/code/experiments/run_fev_bench_official.py.
It estimates FM vs seasonal-naive WAPE log-ratios using paired series/window
units and bootstrap standard errors.  The estimator is intentionally
metric-specific: it does not reuse proxy 1/n variances and it does not claim to
repair SQL/MASE unless prediction-level metric definitions are added.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


CHRONOS_BOLT_RUN_BY_TASK = {
    "rohlik_orders_1W": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "rohlik_orders_1D": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "favorita_transactions_1M": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "favorita_transactions_1W": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "favorita_transactions_1D": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "hierarchical_sales_1W": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "hierarchical_sales_1D": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "favorita_stores_1M": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "walmart": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "restaurant": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "rohlik_sales_1D": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "rohlik_sales_1W": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "rossmann_1W": "fev_v1_9_chronos_bolt_quantile_batch_a",
    "rossmann_1D": "fev_v1_9_chronos_bolt_quantile_batch_b",
    "hermes": "fev_v1_9_chronos_bolt_quantile_batch_b",
    "favorita_stores_1D": "fev_v1_9_chronos_bolt_quantile_batch_c",
    "favorita_stores_1W": "fev_v1_9_chronos_bolt_quantile_batch_c",
    "m5_1M": "fev_v1_9_chronos_bolt_quantile_m5",
    "m5_1W": "fev_v1_9_chronos_bolt_quantile_m5",
    "m5_1D": "fev_v1_9_chronos_bolt_quantile_m5",
}

CHRONOS2_RUN_BY_TASK = {
    "rohlik_orders_1W": "fev_v1_9_chronos2_small",
    "rohlik_orders_1D": "fev_v1_9_chronos2_small",
    "rohlik_sales_1W": "fev_v1_9_chronos2_missing_rohlik_sales_1w",
    "rohlik_sales_1D": "fev_v1_9_chronos2_missing_retail_rest",
    "favorita_transactions_1M": "fev_v1_9_chronos2_small",
    "favorita_transactions_1W": "fev_v1_9_chronos2_small",
    "favorita_transactions_1D": "fev_v1_9_chronos2_small",
    "hierarchical_sales_1W": "fev_v1_9_chronos2_small",
    "hierarchical_sales_1D": "fev_v1_9_chronos2_small",
    "favorita_stores_1M": "fev_v1_9_chronos2_medium_a",
    "favorita_stores_1W": "fev_v1_9_chronos2_missing_retail_rest",
    "favorita_stores_1D": "fev_v1_9_chronos2_missing_retail_rest",
    "walmart": "fev_v1_9_chronos2_medium_a",
    "restaurant": "fev_v1_9_chronos2_medium_a",
    "rossmann_1W": "fev_v1_9_chronos2_missing_retail_rest",
    "rossmann_1D": "fev_v1_9_chronos2_missing_retail_rest",
    "hermes": "fev_v1_9_chronos2_missing_retail_rest",
    "m5_1M": "fev_v1_9_chronos2_missing_retail_rest",
    "m5_1W": "fev_v1_9_chronos2_missing_retail_rest",
    "m5_1D": "fev_v1_9_chronos2_missing_retail_rest",
}

TIREX_RUN_BY_TASK = {
    task: "fev_v1_10_tirex_official_retail"
    for task in CHRONOS_BOLT_RUN_BY_TASK
}

RUN_BY_TASK = {
    "chronos_bolt_tiny": CHRONOS_BOLT_RUN_BY_TASK,
    "chronos2": CHRONOS2_RUN_BY_TASK,
    "tirex": TIREX_RUN_BY_TASK,
}

OUTPUT_PREFIX = {
    "chronos_bolt_tiny": "fev_chronos_bolt_paired_wape",
    "chronos2": "fev_chronos2_paired_wape",
    "tirex": "fev_tirex_paired_wape",
}


def _metrics_path(root: Path, run_id: str, task: str, model: str) -> Path:
    return root / run_id / task / model / "per_series_window_metrics.csv"


def load_paired_metrics(root: Path, baseline_run: str, model_name: str) -> pd.DataFrame:
    frames = []
    run_by_task = RUN_BY_TASK[model_name]
    for task, model_run in run_by_task.items():
        model_path = _metrics_path(root, model_run, task, model_name)
        baseline_path = _metrics_path(root, baseline_run, task, "seasonal_naive")
        if not model_path.exists():
            raise FileNotFoundError(model_path)
        if not baseline_path.exists():
            raise FileNotFoundError(baseline_path)

        model = pd.read_csv(model_path)
        baseline = pd.read_csv(baseline_path)
        key_cols = ["task_name", "window_idx", "series_id"]
        paired = baseline[key_cols + ["WAPE", "n_obs"]].merge(
            model[key_cols + ["WAPE", "n_obs"]],
            on=key_cols,
            how="inner",
            suffixes=("_baseline", "_model"),
            validate="one_to_one",
        )
        paired["task_name"] = task
        paired["model_name"] = model_name
        paired["model_run"] = model_run
        frames.append(paired)
    return pd.concat(frames, ignore_index=True)


def _safe_log_ratio(model_values: pd.Series, baseline_values: pd.Series) -> float:
    model_mean = model_values.dropna().mean()
    baseline_mean = baseline_values.dropna().mean()
    if model_mean <= 0 or baseline_mean <= 0:
        return np.nan
    return float(np.log(model_mean / baseline_mean))


def task_contrasts(paired: pd.DataFrame, model_name: str) -> pd.DataFrame:
    rows = []
    for task, group in paired.groupby("task_name", sort=True):
        valid = group.dropna(subset=["WAPE_baseline", "WAPE_model"])
        rows.append(
            {
                "contrast_id": f"{task}__{model_name}__vs__seasonal_naive__WAPE",
                "task_name": task,
                "model_name": model_name,
                "baseline_name": "seasonal_naive",
                "metric": "mean_series_window_WAPE",
                "n_pairs": len(group),
                "n_valid_pairs": len(valid),
                "model_wape_mean": valid["WAPE_model"].mean(),
                "baseline_wape_mean": valid["WAPE_baseline"].mean(),
                "log_ratio": _safe_log_ratio(valid["WAPE_model"], valid["WAPE_baseline"]),
            }
        )
    return pd.DataFrame(rows)


def bootstrap_task_log_ratios(
    paired: pd.DataFrame,
    *,
    model_name: str,
    n_boot: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    draws = []
    for task, group in paired.groupby("task_name", sort=True):
        valid = group.dropna(subset=["WAPE_baseline", "WAPE_model"])
        by_series = (
            valid.groupby("series_id", sort=True)
            .agg(
                baseline_sum=("WAPE_baseline", "sum"),
                model_sum=("WAPE_model", "sum"),
                n_pairs=("WAPE_baseline", "size"),
            )
            .reset_index()
        )
        baseline_sum = by_series["baseline_sum"].to_numpy(dtype=np.float64)
        model_sum = by_series["model_sum"].to_numpy(dtype=np.float64)
        n_pairs = by_series["n_pairs"].to_numpy(dtype=np.float64)
        n_series = len(by_series)
        for boot_idx in range(n_boot):
            sampled_idx = rng.integers(0, n_series, size=n_series)
            baseline_mean = baseline_sum[sampled_idx].sum() / n_pairs[sampled_idx].sum()
            model_mean = model_sum[sampled_idx].sum() / n_pairs[sampled_idx].sum()
            log_ratio = np.nan
            if baseline_mean > 0 and model_mean > 0:
                log_ratio = float(np.log(model_mean / baseline_mean))
            draws.append(
                {
                    "bootstrap_idx": boot_idx,
                    "contrast_id": f"{task}__{model_name}__vs__seasonal_naive__WAPE",
                    "task_name": task,
                    "log_ratio": log_ratio,
                }
            )
    return pd.DataFrame(draws)


def covariance_from_draws(draws: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = draws.pivot(index="bootstrap_idx", columns="contrast_id", values="log_ratio")
    cov = wide.cov()
    cov_long = cov.rename_axis(index="contrast_id_row", columns="contrast_id_col").stack().reset_index()
    cov_long.columns = ["contrast_id_row", "contrast_id_col", "covariance"]
    return cov, cov_long


def add_bootstrap_intervals(contrasts: pd.DataFrame, draws: pd.DataFrame) -> pd.DataFrame:
    stats = (
        draws.groupby("contrast_id")["log_ratio"]
        .agg(
            bootstrap_mean="mean",
            bootstrap_se="std",
            ci_low=lambda x: np.nanquantile(x, 0.025),
            ci_high=lambda x: np.nanquantile(x, 0.975),
        )
        .reset_index()
    )
    out = contrasts.merge(stats, on="contrast_id", how="left", validate="one_to_one")
    out["ratio"] = np.exp(out["log_ratio"])
    out["ratio_ci_low"] = np.exp(out["ci_low"])
    out["ratio_ci_high"] = np.exp(out["ci_high"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build fev-bench paired bootstrap report.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("benchmark/results/fev_bench_official"),
    )
    parser.add_argument("--baseline-run", default="fev_v1_9_baseline_all_retail")
    parser.add_argument(
        "--model-name",
        default="chronos_bolt_tiny",
        choices=sorted(RUN_BY_TASK),
    )
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/figures"),
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    paired = load_paired_metrics(args.root, args.baseline_run, args.model_name)
    contrasts = task_contrasts(paired, args.model_name)
    draws = bootstrap_task_log_ratios(
        paired,
        model_name=args.model_name,
        n_boot=args.n_boot,
        seed=args.seed,
    )
    cov, cov_long = covariance_from_draws(draws)
    contrasts = add_bootstrap_intervals(contrasts, draws)

    prefix = OUTPUT_PREFIX[args.model_name]
    paired.to_csv(args.output_dir / f"{prefix}_units.csv", index=False)
    contrasts.to_csv(args.output_dir / f"{prefix}_contrasts.csv", index=False)
    draws.to_csv(args.output_dir / f"{prefix}_bootstrap_draws.csv", index=False)
    cov.to_csv(args.output_dir / f"{prefix}_covariance.csv")
    cov_long.to_csv(args.output_dir / f"{prefix}_covariance_long.csv", index=False)

    print(f"Paired units: {len(paired):,}")
    print(f"Contrasts: {len(contrasts):,}")
    print(f"Bootstrap draws: {len(draws):,}")
    print(f"Covariance shape: {cov.shape[0]} x {cov.shape[1]}")
    print(contrasts[["task_name", "log_ratio", "bootstrap_se", "ci_low", "ci_high"]].to_string(index=False))


if __name__ == "__main__":
    main()
