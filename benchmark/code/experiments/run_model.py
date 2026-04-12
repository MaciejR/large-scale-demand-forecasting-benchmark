"""
Single model runner with MLflow tracking.
Entry point for Azure ML jobs and local testing.
"""

import argparse
import os
import sys
import tempfile
import time

import mlflow
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.loaders.m5 import load_m5
from evaluation.metrics import aggregate_metrics, wape
from evaluation.rolling import rolling_forecast
from models.baselines.ets import ets_forecast
from models.baselines.naive import naive_forecast
from models.ml.lightgbm import LightGBMForecaster


def evaluate_lightgbm(df, horizon, min_train_size):
    """Train LightGBM globally then evaluate per-series with rolling origin."""
    lgbm = LightGBMForecaster()
    lgbm.fit(df)

    outputs = []
    for sid, g in df.groupby("series_id"):
        g = g.sort_values("ds").reset_index(drop=True)
        series_df = g[["series_id", "ds", "y"]].copy()

        for t in range(min_train_size, len(g) - horizon + 1, horizon):
            hist = series_df.iloc[:t]
            test = g.iloc[t : t + horizon]
            pred = lgbm.predict(hist, horizon)

            for i in range(horizon):
                outputs.append(
                    {
                        "series_id": sid,
                        "y_true": test["y"].iloc[i],
                        "y_pred": pred.iloc[i],
                    }
                )

    return pd.DataFrame(outputs)


def run_single_model(model_name, df, horizon, min_train_size):
    """Run a single model and return (results_df, metrics_df, runtime)."""
    start = time.time()

    if model_name == "naive":
        results = rolling_forecast(df, horizon, min_train_size, naive_forecast)
    elif model_name == "ets":
        results = rolling_forecast(df, horizon, min_train_size, ets_forecast)
    elif model_name == "lightgbm":
        results = evaluate_lightgbm(df, horizon, min_train_size)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    runtime = time.time() - start
    metrics_df = aggregate_metrics(results)
    return metrics_df, runtime


def log_to_mlflow(model_name, dataset, horizon, min_train_size, metrics_df, runtime,
                  n_series, tags):
    """Log params, metrics, and artifacts to MLflow child run."""
    with mlflow.start_run(run_name=model_name, nested=True):
        mlflow.log_param("model", model_name)
        mlflow.log_param("dataset", dataset)
        mlflow.log_param("horizon", horizon)
        mlflow.log_param("min_train_size", min_train_size)
        mlflow.log_param("n_series", n_series)

        mlflow.log_metric("MAE_mean", metrics_df["MAE"].mean())
        mlflow.log_metric("MAE_std", metrics_df["MAE"].std())
        mlflow.log_metric("sMAPE_mean", metrics_df["sMAPE"].mean())
        mlflow.log_metric("sMAPE_std", metrics_df["sMAPE"].std())
        mlflow.log_metric("WAPE_mean", metrics_df["WAPE"].mean())
        mlflow.log_metric("runtime_sec", runtime)

        for key, value in tags.items():
            mlflow.set_tag(key, value)

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "per_series_metrics.csv")
            metrics_df.to_csv(csv_path, index=False)
            mlflow.log_artifact(csv_path)


def main():
    parser = argparse.ArgumentParser(description="Run a single forecasting model")
    parser.add_argument("--model", required=True, choices=["naive", "ets", "lightgbm"])
    parser.add_argument("--dataset", default="m5")
    parser.add_argument("--horizon", type=int, default=7)
    parser.add_argument("--min-train-size", type=int, default=100)
    parser.add_argument("--sales-path", default=None)
    parser.add_argument("--calendar-path", default=None)
    parser.add_argument("--max-series", type=int, default=None,
                        help="Limit number of series for quick testing")
    args = parser.parse_args()

    sales_path = args.sales_path or os.environ.get(
        "M5_SALES_PATH", "data/m5/sales_train_validation.csv"
    )
    calendar_path = args.calendar_path or os.environ.get(
        "M5_CALENDAR_PATH", "data/m5/calendar.csv"
    )

    print(f"Loading {args.dataset} data from {sales_path}...")
    df = load_m5(sales_path, calendar_path)

    if args.max_series:
        series_ids = df["series_id"].unique()[: args.max_series]
        df = df[df["series_id"].isin(series_ids)]
        print(f"Limited to {len(series_ids)} series")

    n_series = df["series_id"].nunique()
    print(f"Dataset: {n_series} series, {len(df)} rows")
    print(f"Running {args.model} with horizon={args.horizon}...")

    metrics_df, runtime = run_single_model(
        args.model, df, args.horizon, args.min_train_size
    )

    tags = {"phase": "phase1", "eval_method": "rolling_origin"}

    print(f"Logging to MLflow...")
    log_to_mlflow(
        args.model, args.dataset, args.horizon, args.min_train_size,
        metrics_df, runtime, n_series, tags,
    )

    print(f"Done. Runtime: {runtime:.1f}s")
    print(f"  MAE_mean:   {metrics_df['MAE'].mean():.4f}")
    print(f"  sMAPE_mean: {metrics_df['sMAPE'].mean():.2f}")
    print(f"  WAPE_mean:  {metrics_df['WAPE'].mean():.4f}")


if __name__ == "__main__":
    main()
