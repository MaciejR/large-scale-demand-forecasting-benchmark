"""Combine Source B matched-panel reruns into audit tables.

The paired-panel runner writes one directory per model family run.  This report
combines compatible runs that share dataset, horizon, series IDs, and forecast
origins, then computes paired WAPE log-ratios against the best baseline in the
same matched panel.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = ROOT / "benchmark" / "results" / "source_b_paired_panel"
FIG_DIR = ROOT / "analysis" / "figures"
BASELINE_MODELS = {
    "seasonal_naive",
    "lightgbm_cov",
    "lightgbm_direct",
    "lightgbm_direct_scaled",
}


def read_run(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_path = run_dir / "cell_summary.csv"
    metrics_path = run_dir / "per_series_metrics.csv"
    ledger_path = run_dir / "run_ledger.csv"
    if not summary_path.exists() or not metrics_path.exists():
        raise FileNotFoundError(f"Missing summary/metrics in {run_dir}")
    summary = pd.read_csv(summary_path)
    metrics = pd.read_csv(metrics_path)
    if ledger_path.exists():
        ledger = pd.read_csv(ledger_path)
    else:
        ledger = pd.DataFrame()
    summary["source_run_dir"] = run_dir.name
    metrics["source_run_dir"] = run_dir.name
    if not ledger.empty:
        ledger["source_run_dir"] = run_dir.name
    metrics["series_id"] = metrics["series_id"].astype(str)
    return summary, metrics, ledger


def aggregate_runs(run_dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summaries = []
    metrics = []
    ledgers = []
    for run_dir in run_dirs:
        s, m, l = read_run(run_dir)
        summaries.append(s)
        metrics.append(m)
        if not l.empty:
            ledgers.append(l)
    return (
        pd.concat(summaries, ignore_index=True),
        pd.concat(metrics, ignore_index=True),
        pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame(),
    )


def paired_log_ratio(
    model_rows: pd.DataFrame,
    baseline_rows: pd.DataFrame,
    n_boot: int,
    rng: np.random.Generator,
) -> dict:
    paired = model_rows.merge(
        baseline_rows,
        on="series_id",
        suffixes=("_model", "_baseline"),
        how="inner",
    )
    if paired.empty:
        return {
            "n_series_paired": 0,
            "model_WAPE_aggregate": np.nan,
            "baseline_WAPE_aggregate": np.nan,
            "log_ratio": np.nan,
            "bootstrap_se": np.nan,
            "ci95_low": np.nan,
            "ci95_high": np.nan,
        }

    model_err = paired["abs_error_model"].to_numpy(float)
    model_y = paired["abs_y_model"].to_numpy(float)
    base_err = paired["abs_error_baseline"].to_numpy(float)
    base_y = paired["abs_y_baseline"].to_numpy(float)

    model_wape = model_err.sum() / model_y.sum()
    base_wape = base_err.sum() / base_y.sum()
    log_ratio = np.log(model_wape / base_wape)

    boot = []
    n = len(paired)
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        mw = model_err[idx].sum() / model_y[idx].sum()
        bw = base_err[idx].sum() / base_y[idx].sum()
        if mw > 0 and bw > 0:
            boot.append(np.log(mw / bw))
    boot = np.asarray(boot)
    return {
        "n_series_paired": n,
        "model_WAPE_aggregate": model_wape,
        "baseline_WAPE_aggregate": base_wape,
        "log_ratio": log_ratio,
        "bootstrap_se": np.std(boot, ddof=1) if len(boot) > 1 else np.nan,
        "ci95_low": np.quantile(boot, 0.025) if len(boot) else np.nan,
        "ci95_high": np.quantile(boot, 0.975) if len(boot) else np.nan,
    }


def build_contrast_definitions(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (dataset, horizon), cell_summary in summary.groupby(["dataset", "horizon"], sort=False):
        baselines = cell_summary[cell_summary["model_name"].isin(BASELINE_MODELS)]
        if baselines.empty:
            continue
        best_baseline = baselines.sort_values("WAPE_aggregate").iloc[0]["model_name"]
        fm_names = sorted(
            name for name in cell_summary["model_name"].unique()
            if name not in BASELINE_MODELS
        )
        for model_name in fm_names:
            rows.append(
                {
                    "dataset": dataset,
                    "horizon": horizon,
                    "model_name": model_name,
                    "baseline_model": best_baseline,
                }
            )
    contrasts = pd.DataFrame(rows)
    if contrasts.empty:
        return contrasts
    contrasts["contrast_id"] = contrasts.apply(
        lambda row: (
            f"{row['dataset']}_h{int(row['horizon'])}_"
            f"{row['model_name']}_vs_{row['baseline_model']}"
        ),
        axis=1,
    )
    return contrasts


def _series_metric_maps(
    metrics: pd.DataFrame,
    dataset: str,
    horizon: int,
    model_name: str,
) -> pd.DataFrame:
    rows = metrics[
        (metrics["dataset"] == dataset)
        & (metrics["horizon"] == horizon)
        & (metrics["model_name"] == model_name)
    ][["series_id", "abs_error", "abs_y"]].copy()
    rows["series_id"] = rows["series_id"].astype(str)
    return rows.set_index("series_id").sort_index()


def _log_ratio_from_series(
    model_map: pd.DataFrame,
    baseline_map: pd.DataFrame,
    series_ids: np.ndarray | list[str] | None = None,
) -> tuple[float, float, float, int]:
    if series_ids is None:
        paired = model_map.join(
            baseline_map,
            how="inner",
            lsuffix="_model",
            rsuffix="_baseline",
        )
    else:
        sampled = pd.Index(series_ids, dtype="object")
        paired = pd.DataFrame(
            {
                "abs_error_model": model_map["abs_error"].reindex(sampled).to_numpy(float),
                "abs_y_model": model_map["abs_y"].reindex(sampled).to_numpy(float),
                "abs_error_baseline": baseline_map["abs_error"].reindex(sampled).to_numpy(float),
                "abs_y_baseline": baseline_map["abs_y"].reindex(sampled).to_numpy(float),
            }
        ).dropna()
    if paired.empty:
        return np.nan, np.nan, np.nan, 0

    model_wape = paired["abs_error_model"].sum() / paired["abs_y_model"].sum()
    baseline_wape = paired["abs_error_baseline"].sum() / paired["abs_y_baseline"].sum()
    if model_wape <= 0 or baseline_wape <= 0:
        return model_wape, baseline_wape, np.nan, len(paired)
    return model_wape, baseline_wape, float(np.log(model_wape / baseline_wape)), len(paired)


def compute_fm_contrasts_with_covariance(
    summary: pd.DataFrame,
    metrics: pd.DataFrame,
    n_boot: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute paired log-ratios and shared-bootstrap covariance matrix.

    Resampling is shared within each dataset: one bootstrap sample of series IDs
    is used for every horizon/model contrast in that dataset.  This captures the
    empirical covariance among contrasts that share series, actuals, and
    baselines.  Different datasets are sampled independently, yielding a
    block-diagonal covariance structure across datasets.
    """

    contrasts = build_contrast_definitions(summary)
    if contrasts.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty

    metrics = metrics.copy()
    metrics["series_id"] = metrics["series_id"].astype(str)
    rng = np.random.default_rng(seed)

    contrast_maps = {}
    observed_rows = []
    for row in contrasts.itertuples(index=False):
        model_map = _series_metric_maps(metrics, row.dataset, row.horizon, row.model_name)
        baseline_map = _series_metric_maps(metrics, row.dataset, row.horizon, row.baseline_model)
        model_wape, baseline_wape, log_ratio, n_series = _log_ratio_from_series(
            model_map,
            baseline_map,
        )
        contrast_maps[row.contrast_id] = {
            "dataset": row.dataset,
            "model_map": model_map,
            "baseline_map": baseline_map,
        }
        observed_rows.append(
            {
                "dataset": row.dataset,
                "horizon": row.horizon,
                "model_name": row.model_name,
                "baseline_model": row.baseline_model,
                "contrast_id": row.contrast_id,
                "n_series_paired": n_series,
                "model_WAPE_aggregate": model_wape,
                "baseline_WAPE_aggregate": baseline_wape,
                "log_ratio": log_ratio,
            }
        )

    observed = pd.DataFrame(observed_rows)
    contrast_ids = observed["contrast_id"].tolist()
    draws = np.full((n_boot, len(contrast_ids)), np.nan)

    dataset_series = {
        dataset: np.array(sorted(group["series_id"].astype(str).unique()), dtype=object)
        for dataset, group in metrics.groupby("dataset", sort=False)
    }
    for b in range(n_boot):
        sampled_by_dataset = {
            dataset: rng.choice(series_ids, size=len(series_ids), replace=True)
            for dataset, series_ids in dataset_series.items()
        }
        for j, contrast_id in enumerate(contrast_ids):
            maps = contrast_maps[contrast_id]
            sample_ids = sampled_by_dataset[maps["dataset"]]
            _, _, log_ratio, _ = _log_ratio_from_series(
                maps["model_map"],
                maps["baseline_map"],
                sample_ids,
            )
            draws[b, j] = log_ratio

    draw_cols = [f"draw_{i + 1}" for i in range(n_boot)]
    draws_df = pd.DataFrame(draws.T, columns=draw_cols)
    draws_df.insert(0, "contrast_id", contrast_ids)

    cov = np.cov(draws, rowvar=False)
    cov_df = pd.DataFrame(cov, index=contrast_ids, columns=contrast_ids)
    cov_df.insert(0, "contrast_id", contrast_ids)

    summary_rows = []
    for j, contrast_id in enumerate(contrast_ids):
        boot = draws[:, j]
        boot = boot[np.isfinite(boot)]
        summary_rows.append(
            {
                "contrast_id": contrast_id,
                "bootstrap_se": np.std(boot, ddof=1) if len(boot) > 1 else np.nan,
                "ci95_low": np.quantile(boot, 0.025) if len(boot) else np.nan,
                "ci95_high": np.quantile(boot, 0.975) if len(boot) else np.nan,
                "n_boot": n_boot,
            }
        )
    boot_summary = pd.DataFrame(summary_rows)
    fm_contrasts = observed.merge(boot_summary, on="contrast_id", how="left")
    fm_contrasts = fm_contrasts[
        [
            "dataset",
            "horizon",
            "model_name",
            "baseline_model",
            "n_series_paired",
            "model_WAPE_aggregate",
            "baseline_WAPE_aggregate",
            "log_ratio",
            "bootstrap_se",
            "ci95_low",
            "ci95_high",
            "n_boot",
            "contrast_id",
        ]
    ]

    long_rows = []
    cov_values = cov_df.set_index("contrast_id")
    std = np.sqrt(np.diag(cov_values.to_numpy(float)))
    for i, ci in enumerate(contrast_ids):
        for j, cj in enumerate(contrast_ids):
            covariance = float(cov_values.loc[ci, cj])
            denom = std[i] * std[j]
            long_rows.append(
                {
                    "contrast_i": ci,
                    "contrast_j": cj,
                    "covariance": covariance,
                    "correlation": covariance / denom if denom > 0 else np.nan,
                }
            )
    cov_long = pd.DataFrame(long_rows)

    return fm_contrasts, draws_df, cov_df, cov_long


def compute_fm_contrasts(
    summary: pd.DataFrame,
    metrics: pd.DataFrame,
    n_boot: int,
    seed: int,
) -> pd.DataFrame:
    fm_contrasts, _, _, _ = compute_fm_contrasts_with_covariance(
        summary,
        metrics,
        n_boot,
        seed,
    )
    return fm_contrasts


def compute_baseline_protocol_contrasts(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (dataset, horizon), group in summary.groupby(["dataset", "horizon"], sort=False):
        values = dict(zip(group["model_name"], group["WAPE_aggregate"]))
        if "lightgbm_cov" in values and "lightgbm_direct" in values:
            rows.append(
                {
                    "dataset": dataset,
                    "horizon": horizon,
                    "contrast": "direct_minus_recursive",
                    "recursive_WAPE_aggregate": values["lightgbm_cov"],
                    "direct_WAPE_aggregate": values["lightgbm_direct"],
                    "relative_change": values["lightgbm_direct"] / values["lightgbm_cov"] - 1,
                }
            )
        if "lightgbm_direct" in values and "lightgbm_direct_scaled" in values:
            rows.append(
                {
                    "dataset": dataset,
                    "horizon": horizon,
                    "contrast": "direct_scaled_minus_direct",
                    "recursive_WAPE_aggregate": values.get("lightgbm_cov", np.nan),
                    "direct_WAPE_aggregate": values["lightgbm_direct"],
                    "scaled_WAPE_aggregate": values["lightgbm_direct_scaled"],
                    "relative_change": values["lightgbm_direct_scaled"] / values["lightgbm_direct"] - 1,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runs",
        nargs="+",
        default=[
            "source_b_repair_baselines_m5_rohlik_100_v2",
            "source_b_repair_fm_chronos_bolt_m5_rohlik_100",
            "source_b_repair_fm_chronos2_m5_rohlik_100",
        ],
    )
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260714)
    args = parser.parse_args()

    run_root = Path(args.run_root)
    run_dirs = [run_root / run for run in args.runs]
    summary, metrics, ledger = aggregate_runs(run_dirs)

    fm_contrasts, boot_draws, covariance, covariance_long = compute_fm_contrasts_with_covariance(
        summary,
        metrics,
        args.n_bootstrap,
        args.seed,
    )
    protocol = compute_baseline_protocol_contrasts(summary)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(FIG_DIR / "source_b_paired_panel_cell_summary.csv", index=False)
    metrics.to_csv(FIG_DIR / "source_b_paired_panel_per_series_metrics.csv", index=False)
    if not ledger.empty:
        ledger.to_csv(FIG_DIR / "source_b_paired_panel_run_ledger.csv", index=False)
    fm_contrasts.to_csv(FIG_DIR / "source_b_paired_panel_fm_vs_best_baseline.csv", index=False)
    boot_draws.to_csv(FIG_DIR / "source_b_paired_panel_bootstrap_draws.csv", index=False)
    covariance.to_csv(FIG_DIR / "source_b_paired_panel_logratio_covariance.csv", index=False)
    covariance_long.to_csv(FIG_DIR / "source_b_paired_panel_logratio_covariance_long.csv", index=False)
    protocol.to_csv(FIG_DIR / "source_b_paired_panel_baseline_protocol_contrasts.csv", index=False)

    print("Wrote paired-panel Source B report tables to", FIG_DIR)
    print(fm_contrasts.to_string(index=False))
    print(protocol.to_string(index=False))


if __name__ == "__main__":
    main()
