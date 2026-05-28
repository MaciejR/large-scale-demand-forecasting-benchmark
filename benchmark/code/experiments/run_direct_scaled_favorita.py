"""
Phase F extension: direct-LightGBM with horizon-scaled tree budget on Favorita.

Tests the training-budget artefact hypothesis from §5.3.5:
  "direct LGBM's horizon-growth penalty on Favorita is budget-bound
   (fixed 300 trees per head), not protocol-intrinsic."

Design:
  - Baseline (already in results): n_estimators = 300, flat across horizons
  - Scaled: n_estimators = 300 * (h / 7) per head
      h=7  → 300 trees  (same as baseline, serves as control)
      h=14 → 600 trees
      h=28 → 1200 trees

If the WAPE gap between h=7 and h=28 shrinks materially with the scaled
budget, the artefact is confirmed and the direct-vs-recursive comparison
in §5.3.5 is budget-confounded (not protocol-intrinsic).

Logged to MLflow as model_name = "lightgbm_direct_scaled".

Usage (from repo root):
    cd ~/Documents/Repos/large-scale-demand-forecasting-benchmark
    nohup python benchmark/code/experiments/run_direct_scaled_favorita.py \
        > logs/direct_scaled_favorita.log 2>&1 &
    echo $!
"""

import argparse
import os
import sys
import time
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "benchmark" / "code"))

from data.loaders.favorita import load_favorita, KNOWN_DYNAMIC_COLUMNS
from evaluation.cost import CostTracker
from evaluation.metrics import aggregate_metrics

MODEL_NAME = "lightgbm_direct_scaled"
HARDWARE = "M_SERIES_MAC"
LAGS = (1, 7, 14)
WINDOWS = (7, 14)
BASE_ESTIMATORS = 300      # trees at h=7 (matches existing baseline)
BASE_HORIZON = 7           # reference horizon for scaling
TRAIN_FRACTION = 0.8
TRAIN_WINDOW_DAYS = 365
MIN_TRAIN_SIZE = 100


def _n_estimators(horizon: int) -> int:
    """Scale tree budget linearly with horizon relative to h=7 baseline."""
    return int(BASE_ESTIMATORS * horizon / BASE_HORIZON)


def _features_at_step(y_wide, cov_wide, dayofweek, t, k, covariate_cols, n_series):
    cols = []
    for lag in LAGS:
        cols.append(y_wide[:, t - lag])
    for w in WINDOWS:
        cols.append(y_wide[:, t - w: t].mean(axis=1))
    cols.append(np.full(n_series, dayofweek[t + k], dtype=np.float32))
    for cname in covariate_cols:
        cols.append(cov_wide[cname][:, t + k])
    return np.column_stack(cols).astype(np.float32, copy=False)


def run_direct_scaled(df: pd.DataFrame, horizon: int, metadata: dict) -> pd.DataFrame:
    from lightgbm import LGBMRegressor

    covariate_cols = list(metadata.get("known_dynamic_columns", []))
    n_est = _n_estimators(horizon)
    print(f"  horizon={horizon}, n_estimators={n_est} ({BASE_ESTIMATORS} × {horizon}/{BASE_HORIZON})")

    df = df.sort_values(["series_id", "ds"]).reset_index(drop=True)
    series_ids = df["series_id"].unique()
    dates = np.sort(df["ds"].unique())
    n_series = len(series_ids)
    n_days = len(dates)

    print(f"  Pivoting to wide ({n_series} series × {n_days} days)...")
    y_wide = (df.pivot(index="series_id", columns="ds", values="y")
                .reindex(series_ids).fillna(0).values.astype(np.float32))
    cov_wide = {}
    for col in covariate_cols:
        cov_wide[col] = (df.pivot(index="series_id", columns="ds", values=col)
                           .reindex(series_ids).fillna(0).values.astype(np.float32))

    max_lag = max(max(LAGS), max(WINDOWS))
    train_until = int(n_days * TRAIN_FRACTION)
    train_start = max(max_lag, train_until - TRAIN_WINDOW_DAYS)
    dayofweek = pd.to_datetime(dates).dayofweek.values.astype(np.int8)

    n_features = len(LAGS) + len(WINDOWS) + 1 + len(covariate_cols)

    # Train h separate models
    models = []
    for k in range(horizon):
        t_max = train_until - k
        n_t = t_max - train_start
        print(f"  [k={k:2d}] building matrix ({n_series * n_t:,} rows), fitting {n_est} trees...")
        X_k = np.empty((n_series * n_t, n_features), dtype=np.float32)
        y_k = np.empty(n_series * n_t, dtype=np.float32)
        for i, t in enumerate(range(train_start, t_max)):
            rs, re = i * n_series, (i + 1) * n_series
            X_k[rs:re] = _features_at_step(y_wide, cov_wide, dayofweek, t, k, covariate_cols, n_series)
            y_k[rs:re] = y_wide[:, t + k]
        lgbm = LGBMRegressor(
            objective="tweedie",
            tweedie_variance_power=1.1,
            learning_rate=0.05,
            num_leaves=63,
            n_estimators=n_est,
            min_child_samples=20,
            verbosity=-1,
        )
        lgbm.fit(X_k, y_k)
        models.append(lgbm)
        del X_k, y_k

    # Evaluate rolling-origin
    print(f"  Evaluating (rolling origin)...")
    eval_starts = list(range(train_until, n_days - horizon + 1, horizon))
    n_eval_days = len(eval_starts) * horizon
    y_pred_wide = np.empty((n_series, n_eval_days), dtype=np.float32)
    eval_t_arr = np.empty(n_eval_days, dtype=np.int32)

    idx = 0
    for t0 in eval_starts:
        for k in range(horizon):
            X_step = _features_at_step(y_wide, cov_wide, dayofweek, t0, k, covariate_cols, n_series)
            pred = np.maximum(models[k].predict(X_step).astype(np.float32), 0.0)
            y_pred_wide[:, idx] = pred
            eval_t_arr[idx] = t0 + k
            idx += 1

    y_true_wide = y_wide[:, eval_t_arr]
    return pd.DataFrame({
        "series_id": np.repeat(series_ids, n_eval_days),
        "y_true": y_true_wide.flatten(),
        "y_pred": y_pred_wide.flatten(),
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-path", default=os.environ.get("FAVORITA_TRAIN_PATH", "data/raw/favorita/train.csv"))
    parser.add_argument("--oil-path", default=os.environ.get("FAVORITA_OIL_PATH", "data/raw/favorita/oil.csv"))
    parser.add_argument("--holidays-path", default=os.environ.get("FAVORITA_HOLIDAYS_PATH", "data/raw/favorita/holidays_events.csv"))
    parser.add_argument("--stores-path", default=os.environ.get("FAVORITA_STORES_PATH", "data/raw/favorita/stores.csv"))
    parser.add_argument("--tx-path", default=os.environ.get("FAVORITA_TX_PATH", "data/raw/favorita/transactions.csv"))
    parser.add_argument("--max-series", type=int, default=None)
    parser.add_argument("--horizons", type=int, nargs="+", default=[7, 14, 28])
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    mlflow.set_tracking_uri(str(REPO_ROOT / "mlruns"))

    print("Loading Favorita...")
    df = load_favorita(
        path_train=args.train_path,
        path_oil=args.oil_path,
        path_holidays=args.holidays_path,
        path_stores=args.stores_path,
        path_transactions=args.tx_path,
        with_covariates=True,
        max_series=args.max_series,
    )
    metadata = {"dataset": "Favorita", "known_dynamic_columns": list(KNOWN_DYNAMIC_COLUMNS)}
    n_series = df["series_id"].nunique()
    print(f"Dataset: {n_series} series")

    for horizon in sorted(args.horizons, reverse=True):  # longest first (hardest)
        n_est = _n_estimators(horizon)
        run_name = f"{MODEL_NAME}_favorita_h{horizon}_n{n_est}"
        print(f"\n[{run_name}]")
        t0 = time.time()

        tracker = CostTracker(hardware=HARDWARE)
        tracker.start()
        results = run_direct_scaled(df, horizon, metadata)
        tracker.stop()
        elapsed = time.time() - t0

        metrics_df = aggregate_metrics(results)
        wape_series = metrics_df["WAPE"].replace([np.inf, -np.inf], np.nan)
        wape_mean = float(wape_series.dropna().mean())
        n_valid = int(wape_series.notna().sum())
        cost_metrics = tracker.to_dict(n_series=n_series)

        print(f"  Runtime: {elapsed:.1f}s ({elapsed/3600:.2f}h)")
        print(f"  WAPE_mean: {wape_mean:.4f} (n_valid={n_valid})")
        print(f"  MAE_mean:  {metrics_df['MAE'].mean():.4f}")
        print(f"  Cost: ${cost_metrics['cost_usd']:.4f}")

        with mlflow.start_run(run_name=run_name):
            mlflow.log_param("model_name", MODEL_NAME)
            mlflow.log_param("dataset", "Favorita")
            mlflow.log_param("horizon", horizon)
            mlflow.log_param("n_estimators_per_head", n_est)
            mlflow.log_param("n_series", n_series)
            mlflow.log_param("hardware", HARDWARE)
            mlflow.log_param("budget_scaling", f"{horizon}/{BASE_HORIZON}x")
            mlflow.log_metric("WAPE_mean", wape_mean)
            mlflow.log_metric("WAPE_n_valid", n_valid)
            mlflow.log_metric("MAE_mean", float(metrics_df["MAE"].mean()))
            mlflow.log_metric("sMAPE_mean", float(metrics_df["sMAPE"].mean()))
            mlflow.log_metric("runtime_sec", elapsed)
            mlflow.log_metric("cost_usd", cost_metrics["cost_usd"])
            mlflow.log_metric("co2_kg", cost_metrics["co2_kg"])
            mlflow.set_tag("hardware", HARDWARE)
            mlflow.set_tag("phase_f_extension", "horizon_scaled_budget")

        print(f"  Logged to MLflow: {run_name}")


if __name__ == "__main__":
    main()
