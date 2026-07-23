"""Build M5 200-trial LightGBM sensitivity tables and paired contrasts.

The six high-budget LightGBM runs are separate one-model run directories.
This script validates an explicit allow-list, combines those runs with the
existing Source B M5 foundation-model per-series metrics, and computes paired
series-bootstrap log-ratio contrasts against the best 200-trial LightGBM
baseline in each horizon.
"""

from __future__ import annotations

import argparse
import json
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "m5_200trial" / "artifact_manifest.json"
DEFAULT_SOURCE_B_METRICS = ROOT / "analysis" / "figures" / "source_b_paired_panel_per_series_metrics.csv"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "m5_200trial"
DEFAULT_FIG_DIR = ROOT / "analysis" / "figures"
FM_MODELS = ["chronos2", "chronos_bolt_tiny", "moirai2", "timesfm25", "tirex"]


def _dataset_seed(seed: int, label: str) -> int:
    return (int(seed) + zlib.crc32(label.encode("utf-8"))) % (2**32)


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"Empty CSV: {path}") from exc


def validate_artifact(manifest: dict, root: Path) -> list[Path]:
    run_root = root / manifest["run_root"]
    if not run_root.exists():
        raise FileNotFoundError(f"Run root does not exist: {run_root}")

    excluded = set(manifest.get("excluded_dirs", []))
    for name in excluded:
        path = run_root / name
        if path.exists():
            raise ValueError(f"Excluded partial run directory is present: {path}")

    required_files = manifest["required_files_per_dir"]
    required_counts = manifest["required_counts"]
    run_dirs = []
    for name in manifest["expected_dirs"]:
        run_dir = run_root / name
        if not run_dir.exists():
            raise FileNotFoundError(f"Expected run directory missing: {run_dir}")
        for filename in required_files:
            path = run_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Required file missing: {path}")
            if path.stat().st_size == 0:
                raise ValueError(f"Required file is empty: {path}")

        summary = _read_csv(run_dir / "cell_summary.csv")
        metrics = _read_csv(run_dir / "per_series_metrics.csv")
        trials = _read_csv(run_dir / "lightgbm_tuning_trials.csv")
        ledger = _read_csv(run_dir / "run_ledger.csv")
        if len(summary) != required_counts["cell_summary_rows"]:
            raise ValueError(f"{run_dir}: expected one cell_summary row, got {len(summary)}")
        if len(metrics) != required_counts["per_series_metrics_rows"]:
            raise ValueError(f"{run_dir}: expected 100 per-series rows, got {len(metrics)}")
        if len(trials) != required_counts["lightgbm_tuning_trials_rows"]:
            raise ValueError(f"{run_dir}: expected 200 tuning trials, got {len(trials)}")
        for frame_name, frame in {
            "cell_summary": summary,
            "per_series_metrics": metrics,
            "lightgbm_tuning_trials": trials,
            "run_ledger": ledger,
        }.items():
            if set(frame["dataset"].astype(str).unique()) != {"M5"}:
                raise ValueError(f"{run_dir}: {frame_name} is not restricted to M5")
        if not summary["model_name"].iloc[0] in {"lightgbm_tuned_cov", "lightgbm_tuned_direct"}:
            raise ValueError(f"{run_dir}: unexpected model_name in cell_summary")
        run_dirs.append(run_dir)
    return run_dirs


def load_200trial_runs(run_dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summaries = []
    metrics = []
    trials = []
    for run_dir in run_dirs:
        summary = _read_csv(run_dir / "cell_summary.csv")
        metric = _read_csv(run_dir / "per_series_metrics.csv")
        trial = _read_csv(run_dir / "lightgbm_tuning_trials.csv")
        summary["source_run_dir"] = run_dir.name
        metric["source_run_dir"] = run_dir.name
        trial["source_run_dir"] = run_dir.name
        summaries.append(summary)
        metrics.append(metric)
        trials.append(trial)
    sort_cols = ["horizon", "model_name", "source_run_dir"]
    summary_df = pd.concat(summaries, ignore_index=True).sort_values(sort_cols).reset_index(drop=True)
    metrics_df = (
        pd.concat(metrics, ignore_index=True)
        .sort_values(["horizon", "model_name", "series_id"])
        .reset_index(drop=True)
    )
    trials_df = (
        pd.concat(trials, ignore_index=True)
        .sort_values(["horizon", "model_name", "trial"])
        .reset_index(drop=True)
    )
    return summary_df, metrics_df, trials_df


def build_tuning_summary(summary: pd.DataFrame, trials: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in summary.itertuples(index=False):
        cell_trials = trials[
            (trials["horizon"] == row.horizon)
            & (trials["model_name"] == row.model_name)
        ].copy()
        best = cell_trials.sort_values("validation_WAPE_aggregate").iloc[0]
        rows.append(
            {
                "dataset": row.dataset,
                "horizon": row.horizon,
                "model_name": row.model_name,
                "protocol": best["protocol"],
                "n_trials": len(cell_trials),
                "best_validation_trial": int(best["trial"]),
                "best_validation_WAPE_aggregate": best["validation_WAPE_aggregate"],
                "test_WAPE_aggregate": row.WAPE_aggregate,
                "test_WAPE_mean": row.WAPE_mean,
                "runtime_sec": row.runtime_sec,
                "wall_clock_sec": row.wall_clock_sec,
                "cost_usd": row.cost_usd,
                "co2_kg": row.co2_kg,
                "source_run_dir": row.source_run_dir,
            }
        )
    return pd.DataFrame(rows).sort_values(["horizon", "model_name"]).reset_index(drop=True)


def best_high_budget_baselines(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for horizon, group in summary.groupby("horizon", sort=True):
        best = group.sort_values("WAPE_aggregate").iloc[0]
        rows.append(
            {
                "dataset": "M5",
                "horizon": horizon,
                "baseline_model": best["model_name"],
                "baseline_WAPE_aggregate": best["WAPE_aggregate"],
                "baseline_WAPE_mean": best["WAPE_mean"],
                "baseline_runtime_sec": best["runtime_sec"],
                "baseline_source_run_dir": best["source_run_dir"],
            }
        )
    return pd.DataFrame(rows)


def _series_maps(metrics: pd.DataFrame, horizon: int, model_name: str) -> dict[str, tuple[float, float]]:
    subset = metrics[
        (metrics["dataset"] == "M5")
        & (metrics["horizon"] == horizon)
        & (metrics["model_name"] == model_name)
    ]
    return {
        str(row.series_id): (float(row.abs_error), float(row.abs_y))
        for row in subset.itertuples(index=False)
        if float(row.abs_y) > 0
    }


def _log_ratio(
    model_map: dict[str, tuple[float, float]],
    baseline_map: dict[str, tuple[float, float]],
    sample_ids: np.ndarray | None = None,
) -> tuple[float, float, float, int]:
    ids = sorted(set(model_map) & set(baseline_map))
    if sample_ids is not None:
        ids = [str(i) for i in sample_ids if str(i) in model_map and str(i) in baseline_map]
    if not ids:
        return np.nan, np.nan, np.nan, 0
    model_err = np.array([model_map[i][0] for i in ids], dtype=float)
    model_y = np.array([model_map[i][1] for i in ids], dtype=float)
    base_err = np.array([baseline_map[i][0] for i in ids], dtype=float)
    base_y = np.array([baseline_map[i][1] for i in ids], dtype=float)
    model_wape = model_err.sum() / model_y.sum()
    baseline_wape = base_err.sum() / base_y.sum()
    return model_wape, baseline_wape, np.log(model_wape / baseline_wape), len(ids)


def compute_fm_vs_high_budget(
    fm_metrics: pd.DataFrame,
    baseline_metrics: pd.DataFrame,
    best_baselines: pd.DataFrame,
    n_boot: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    combined_metrics = pd.concat([fm_metrics, baseline_metrics], ignore_index=True)
    contrast_rows = []
    contrast_maps = {}
    for best in best_baselines.itertuples(index=False):
        baseline_map = _series_maps(combined_metrics, int(best.horizon), best.baseline_model)
        for model_name in FM_MODELS:
            model_map = _series_maps(combined_metrics, int(best.horizon), model_name)
            model_wape, baseline_wape, log_ratio, n_series = _log_ratio(model_map, baseline_map)
            contrast_id = f"M5_h{int(best.horizon)}_{model_name}_vs_{best.baseline_model}_200trial"
            contrast_rows.append(
                {
                    "dataset": "M5",
                    "horizon": int(best.horizon),
                    "model_name": model_name,
                    "baseline_model": best.baseline_model,
                    "baseline_rule": "best_200trial_test_WAPE_aggregate",
                    "n_series_paired": n_series,
                    "model_WAPE_aggregate": model_wape,
                    "baseline_WAPE_aggregate": baseline_wape,
                    "log_ratio": log_ratio,
                    "contrast_id": contrast_id,
                }
            )
            contrast_maps[contrast_id] = {
                "horizon": int(best.horizon),
                "model_map": model_map,
                "baseline_map": baseline_map,
            }

    observed = pd.DataFrame(contrast_rows)
    contrast_ids = observed["contrast_id"].tolist()
    draws = np.full((n_boot, len(contrast_ids)), np.nan)
    all_series = np.array(sorted(combined_metrics["series_id"].astype(str).unique()), dtype=object)
    rng = np.random.default_rng(_dataset_seed(seed, "M5_200trial"))
    for b in range(n_boot):
        sampled = rng.choice(all_series, size=len(all_series), replace=True)
        for j, contrast_id in enumerate(contrast_ids):
            maps = contrast_maps[contrast_id]
            _, _, lr, _ = _log_ratio(maps["model_map"], maps["baseline_map"], sampled)
            draws[b, j] = lr

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
    contrasts = observed.merge(pd.DataFrame(summary_rows), on="contrast_id", how="left")
    covariance = pd.DataFrame(np.cov(draws, rowvar=False), index=contrast_ids, columns=contrast_ids)
    covariance.insert(0, "contrast_id", contrast_ids)
    draws_df = pd.DataFrame(draws.T, columns=[f"draw_{i + 1}" for i in range(n_boot)])
    draws_df.insert(0, "contrast_id", contrast_ids)
    return contrasts.sort_values(["horizon", "model_name"]).reset_index(drop=True), covariance, draws_df


def build_sensitivity_tables(
    manifest_path: Path,
    root: Path,
    source_b_metrics_path: Path,
    output_dir: Path,
    fig_dir: Path,
    n_boot: int,
    seed: int,
) -> dict[str, Path]:
    manifest = load_manifest(manifest_path)
    run_dirs = validate_artifact(manifest, root)
    summary, baseline_metrics, trials = load_200trial_runs(run_dirs)
    tuning_summary = build_tuning_summary(summary, trials)
    best_baselines = best_high_budget_baselines(summary)

    source_b_metrics = pd.read_csv(source_b_metrics_path)
    fm_metrics = source_b_metrics[
        (source_b_metrics["dataset"] == "M5")
        & (source_b_metrics["model_name"].isin(FM_MODELS))
    ].copy()
    contrasts, covariance, draws = compute_fm_vs_high_budget(
        fm_metrics,
        baseline_metrics,
        best_baselines,
        n_boot,
        seed,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "cell_summary": output_dir / "m5_lightgbm_200trial_cell_summary.csv",
        "tuning_summary": output_dir / "m5_lightgbm_200trial_tuning_summary.csv",
        "best_baselines": output_dir / "m5_lightgbm_200trial_best_baselines.csv",
        "contrasts": output_dir / "m5_lightgbm_200trial_fm_vs_best_high_budget_baseline.csv",
        "covariance": output_dir / "m5_lightgbm_200trial_logratio_covariance.csv",
        "draws": output_dir / "m5_lightgbm_200trial_bootstrap_draws.csv",
        "fig_contrasts": fig_dir / "source_b_m5_200trial_fm_vs_best_high_budget_baseline.csv",
        "fig_best_baselines": fig_dir / "source_b_m5_200trial_best_baselines.csv",
    }
    summary.to_csv(outputs["cell_summary"], index=False)
    tuning_summary.to_csv(outputs["tuning_summary"], index=False)
    best_baselines.to_csv(outputs["best_baselines"], index=False)
    contrasts.to_csv(outputs["contrasts"], index=False)
    covariance.to_csv(outputs["covariance"], index=False)
    draws.to_csv(outputs["draws"], index=False)
    contrasts.to_csv(outputs["fig_contrasts"], index=False)
    best_baselines.to_csv(outputs["fig_best_baselines"], index=False)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--source-b-metrics", default=str(DEFAULT_SOURCE_B_METRICS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--fig-dir", default=str(DEFAULT_FIG_DIR))
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260714)
    args = parser.parse_args()

    outputs = build_sensitivity_tables(
        Path(args.manifest),
        Path(args.root),
        Path(args.source_b_metrics),
        Path(args.output_dir),
        Path(args.fig_dir),
        args.n_bootstrap,
        args.seed,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
