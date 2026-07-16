#!/usr/bin/env python3
"""Build a manifest for official fev-bench rerun artifacts.

The fev-bench official reruns include exploratory smoke runs and superseded
point-quantile Chronos-Bolt runs.  This manifest marks only the canonical runs
used for the current methodology repair tables:

- seasonal_naive for all 20 retail tasks;
- Chronos-Bolt-Tiny with true quantiles for all 20 retail tasks;
- Chronos-2 with true quantiles for all 20 retail tasks;
- paired WAPE bootstrap outputs for Chronos-Bolt and Chronos-2.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


RETAIL_TASKS = [
    "rohlik_sales_1D",
    "rohlik_sales_1W",
    "rohlik_orders_1D",
    "rohlik_orders_1W",
    "rossmann_1D",
    "rossmann_1W",
    "restaurant",
    "hermes",
    "walmart",
    "m5_1D",
    "m5_1W",
    "m5_1M",
    "hierarchical_sales_1D",
    "hierarchical_sales_1W",
    "favorita_stores_1D",
    "favorita_stores_1W",
    "favorita_stores_1M",
    "favorita_transactions_1D",
    "favorita_transactions_1W",
    "favorita_transactions_1M",
]

CANONICAL_RUNS = {
    "seasonal_naive": {
        "fev_v1_9_baseline_all_retail": RETAIL_TASKS,
    },
    "chronos_bolt_tiny": {
        "fev_v1_9_chronos_bolt_quantile_batch_a": [
            "rohlik_orders_1W",
            "rohlik_orders_1D",
            "favorita_transactions_1M",
            "favorita_transactions_1W",
            "favorita_transactions_1D",
            "hierarchical_sales_1W",
            "hierarchical_sales_1D",
            "favorita_stores_1M",
            "walmart",
            "restaurant",
            "rohlik_sales_1D",
            "rohlik_sales_1W",
            "rossmann_1W",
        ],
        "fev_v1_9_chronos_bolt_quantile_batch_b": ["rossmann_1D", "hermes"],
        "fev_v1_9_chronos_bolt_quantile_batch_c": [
            "favorita_stores_1D",
            "favorita_stores_1W",
        ],
        "fev_v1_9_chronos_bolt_quantile_m5": ["m5_1M", "m5_1W", "m5_1D"],
    },
    "chronos2": {
        "fev_v1_9_chronos2_small": [
            "rohlik_orders_1W",
            "rohlik_orders_1D",
            "favorita_transactions_1M",
            "favorita_transactions_1W",
            "favorita_transactions_1D",
            "hierarchical_sales_1W",
            "hierarchical_sales_1D",
        ],
        "fev_v1_9_chronos2_medium_a": [
            "favorita_stores_1M",
            "walmart",
            "restaurant",
        ],
        "fev_v1_9_chronos2_missing_rohlik_sales_1w": [
            "rohlik_sales_1W",
        ],
        "fev_v1_9_chronos2_missing_retail_rest": [
            "rohlik_sales_1D",
            "rossmann_1W",
            "hermes",
            "rossmann_1D",
            "favorita_stores_1D",
            "favorita_stores_1W",
            "m5_1M",
            "m5_1D",
            "m5_1W",
        ],
    },
}

BOOTSTRAP_OUTPUTS = {
    "chronos_bolt_tiny": [
        "fev_chronos_bolt_paired_wape_units.csv",
        "fev_chronos_bolt_paired_wape_contrasts.csv",
        "fev_chronos_bolt_paired_wape_bootstrap_draws.csv",
        "fev_chronos_bolt_paired_wape_covariance.csv",
        "fev_chronos_bolt_paired_wape_covariance_long.csv",
    ],
    "chronos2": [
        "fev_chronos2_paired_wape_units.csv",
        "fev_chronos2_paired_wape_contrasts.csv",
        "fev_chronos2_paired_wape_bootstrap_draws.csv",
        "fev_chronos2_paired_wape_covariance.csv",
        "fev_chronos2_paired_wape_covariance_long.csv",
    ],
}


def _artifact_sizes(base: Path) -> dict[str, int | None]:
    return {
        "summary_bytes": (base / "summary.json").stat().st_size
        if (base / "summary.json").exists()
        else None,
        "predictions_bytes": (base / "predictions_long.parquet").stat().st_size
        if (base / "predictions_long.parquet").exists()
        else None,
        "per_series_bytes": (base / "per_series_window_metrics.csv").stat().st_size
        if (base / "per_series_window_metrics.csv").exists()
        else None,
        "run_config_bytes": (base / "run_config.json").stat().st_size
        if (base / "run_config.json").exists()
        else None,
    }


def _read_summary(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def build_run_manifest(root: Path) -> pd.DataFrame:
    rows = []
    for model_name, run_map in CANONICAL_RUNS.items():
        for run_id, tasks in run_map.items():
            for task in tasks:
                base = root / run_id / task / model_name
                summary_path = base / "summary.json"
                row = {
                    "model_name": model_name,
                    "run_id": run_id,
                    "task_name": task,
                    "status": "complete" if summary_path.exists() else "missing",
                    "path": str(base),
                }
                row.update(_artifact_sizes(base))
                if summary_path.exists():
                    summary = _read_summary(summary_path)
                    row.update(
                        {
                            "SQL": summary.get("test_error"),
                            "MASE": summary.get("MASE"),
                            "WAPE": summary.get("WAPE"),
                            "num_forecasts": summary.get("num_forecasts"),
                            "inference_time_s": summary.get("inference_time_s"),
                        }
                    )
                rows.append(row)
    return pd.DataFrame(rows)


def build_coverage(manifest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model_name, group in manifest.groupby("model_name", sort=True):
        complete = group[group["status"] == "complete"]
        rows.append(
            {
                "model_name": model_name,
                "completed_tasks": complete["task_name"].nunique(),
                "expected_tasks": len(group),
                "missing_tasks": ";".join(sorted(set(group["task_name"]) - set(complete["task_name"]))),
                "num_forecasts": int(complete["num_forecasts"].fillna(0).sum()),
                "prediction_bytes": int(complete["predictions_bytes"].fillna(0).sum()),
            }
        )
    return pd.DataFrame(rows)


def build_bootstrap_manifest(figures_dir: Path) -> pd.DataFrame:
    rows = []
    for model_name, filenames in BOOTSTRAP_OUTPUTS.items():
        for filename in filenames:
            path = figures_dir / filename
            rows.append(
                {
                    "model_name": model_name,
                    "artifact": filename,
                    "status": "complete" if path.exists() else "missing",
                    "bytes": path.stat().st_size if path.exists() else None,
                    "path": str(path),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build official fev-bench artifact manifest.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("benchmark/results/fev_bench_official"),
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=Path("analysis/figures"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/figures"),
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_run_manifest(args.root)
    coverage = build_coverage(manifest)
    bootstrap = build_bootstrap_manifest(args.figures_dir)

    manifest.to_csv(args.output_dir / "fev_official_run_manifest.csv", index=False)
    coverage.to_csv(args.output_dir / "fev_official_model_coverage.csv", index=False)
    bootstrap.to_csv(args.output_dir / "fev_official_bootstrap_manifest.csv", index=False)

    missing_runs = manifest[manifest["status"] != "complete"]
    missing_bootstrap = bootstrap[bootstrap["status"] != "complete"]
    print("Run manifest rows:", len(manifest))
    print(coverage.to_string(index=False))
    print("Bootstrap artifacts:", len(bootstrap))
    if not missing_runs.empty:
        print("Missing run artifacts:")
        print(missing_runs[["model_name", "run_id", "task_name"]].to_string(index=False))
    if not missing_bootstrap.empty:
        print("Missing bootstrap artifacts:")
        print(missing_bootstrap[["model_name", "artifact"]].to_string(index=False))


if __name__ == "__main__":
    main()
