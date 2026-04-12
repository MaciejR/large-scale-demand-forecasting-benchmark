"""
Gap-filling experiment runner for the meta-analysis.
Runs missing model x dataset combinations and logs to MLflow.
Entry point for Azure ML jobs.
"""

import argparse
import os
import sys
import tempfile
import time

import mlflow
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.loaders.m5 import load_m5
from evaluation.cost import CostTracker
from evaluation.metrics import aggregate_metrics
from evaluation.rolling import rolling_forecast
from models.baselines.seasonal_naive import seasonal_naive_forecast


def load_dataset(dataset: str, task: str = None, **kwargs):
    """Load dataset by name. Returns (df, metadata)."""
    if dataset == "m5":
        sales_path = kwargs.get("sales_path", os.environ.get(
            "M5_SALES_PATH", "data/m5/sales_train_validation.csv"
        ))
        calendar_path = kwargs.get("calendar_path", os.environ.get(
            "M5_CALENDAR_PATH", "data/m5/calendar.csv"
        ))
        df = load_m5(sales_path, calendar_path)
        return df, {"dataset": "m5", "horizon": kwargs.get("horizon", 7)}

    elif dataset == "gift_eval":
        from data.loaders.gift_eval import load_gift_eval, get_gift_eval_prediction_length
        ds_name = task or "restaurant"
        term = kwargs.get("term", "short")
        df = load_gift_eval(ds_name, term=term)
        horizon = get_gift_eval_prediction_length(ds_name, term)
        return df, {"dataset": f"gift_eval/{ds_name}", "horizon": horizon}

    elif dataset == "fev_bench":
        from data.loaders.fev_bench import load_fev_bench_task
        task_name = task or "m5_1D"
        df, metadata = load_fev_bench_task(task_name)
        return df, metadata

    else:
        raise ValueError(f"Unknown dataset: {dataset}")


def get_model_fn(model_name: str):
    """Return (forecast_fn, is_foundation_model) for a given model name."""
    if model_name == "seasonal_naive":
        return seasonal_naive_forecast, False

    elif model_name == "chronos2":
        from models.foundation.chronos2 import Chronos2Forecaster
        forecaster = Chronos2Forecaster()
        return forecaster.predict, True

    elif model_name == "timesfm25":
        from models.foundation.timesfm25 import TimesFM25Forecaster
        forecaster = TimesFM25Forecaster()
        return forecaster.predict, True

    elif model_name == "moirai2":
        from models.foundation.moirai2 import Moirai2Forecaster
        forecaster = Moirai2Forecaster()
        return forecaster.predict, True

    else:
        raise ValueError(f"Unknown model: {model_name}")


def run_experiment(
    model_name: str,
    df: pd.DataFrame,
    horizon: int,
    min_train_size: int,
    hardware: str,
    max_series: int = None,
):
    """Run a single model on a dataset with cost tracking."""
    if max_series:
        series_ids = df["series_id"].unique()[:max_series]
        df = df[df["series_id"].isin(series_ids)]

    n_series = df["series_id"].nunique()
    forecast_fn, is_gpu = get_model_fn(model_name)

    tracker = CostTracker(hardware=hardware)
    tracker.start()
    results = rolling_forecast(df, horizon, min_train_size, forecast_fn)
    tracker.stop()

    metrics_df = aggregate_metrics(results)
    cost_metrics = tracker.to_dict(n_series=n_series)

    return metrics_df, cost_metrics, n_series


def log_run(
    model_name: str,
    dataset_name: str,
    horizon: int,
    min_train_size: int,
    metrics_df: pd.DataFrame,
    cost_metrics: dict,
    n_series: int,
    tags: dict,
):
    """Log everything to MLflow nested run."""
    with mlflow.start_run(run_name=f"{model_name}_{dataset_name}_h{horizon}", nested=True):
        mlflow.log_param("model", model_name)
        mlflow.log_param("dataset", dataset_name)
        mlflow.log_param("horizon", horizon)
        mlflow.log_param("min_train_size", min_train_size)
        mlflow.log_param("n_series", n_series)

        mlflow.log_metric("MAE_mean", metrics_df["MAE"].mean())
        mlflow.log_metric("MAE_std", metrics_df["MAE"].std())
        mlflow.log_metric("sMAPE_mean", metrics_df["sMAPE"].mean())
        mlflow.log_metric("sMAPE_std", metrics_df["sMAPE"].std())
        mlflow.log_metric("WAPE_mean", metrics_df["WAPE"].mean())

        mlflow.log_metric("runtime_sec", cost_metrics["runtime_sec"])
        mlflow.log_metric("cost_usd", cost_metrics["cost_usd"])
        mlflow.log_metric("co2_kg", cost_metrics["co2_kg"])
        mlflow.log_metric("series_per_second", cost_metrics["series_per_second"])

        for key, value in tags.items():
            mlflow.set_tag(key, value)
        mlflow.set_tag("hardware", cost_metrics["hardware"])

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "per_series_metrics.csv")
            metrics_df.to_csv(csv_path, index=False)
            mlflow.log_artifact(csv_path)


def main():
    parser = argparse.ArgumentParser(description="Run gap-filling experiment")
    parser.add_argument("--model", required=True,
                        choices=["seasonal_naive", "chronos2", "timesfm25", "moirai2",
                                 "lightgbm_cov"])
    parser.add_argument("--dataset", required=True,
                        choices=["m5", "gift_eval", "fev_bench"])
    parser.add_argument("--task", default=None,
                        help="Dataset-specific task (e.g. gift_eval dataset name or fev_bench task)")
    parser.add_argument("--horizon", type=int, default=None,
                        help="Override horizon (uses dataset default if not set)")
    parser.add_argument("--min-train-size", type=int, default=100)
    parser.add_argument("--max-series", type=int, default=None)
    parser.add_argument("--hardware", default="E4DS_V4",
                        choices=["E4DS_V4", "NC6", "T4", "K80", "A100"])
    parser.add_argument("--sales-path", default=None)
    parser.add_argument("--calendar-path", default=None)
    parser.add_argument("--term", default="short", help="GIFT-Eval term")
    args = parser.parse_args()

    print(f"Loading {args.dataset}" + (f"/{args.task}" if args.task else "") + "...")
    df, metadata = load_dataset(
        args.dataset,
        task=args.task,
        sales_path=args.sales_path,
        calendar_path=args.calendar_path,
        horizon=args.horizon,
        term=args.term,
    )

    horizon = args.horizon or metadata.get("horizon", 7)
    dataset_name = metadata.get("dataset", args.dataset)
    if args.task:
        dataset_name = f"{args.dataset}/{args.task}"

    print(f"Dataset: {df['series_id'].nunique()} series, {len(df)} rows")
    print(f"Running {args.model} with horizon={horizon}...")

    metrics_df, cost_metrics, n_series = run_experiment(
        args.model, df, horizon, args.min_train_size,
        args.hardware, args.max_series,
    )

    tags = {"phase": "gap_filling", "eval_method": "rolling_origin", "paper": "meta-analysis"}
    mlflow.set_experiment("meta-analysis-gap-filling")

    with mlflow.start_run(run_name=f"{dataset_name}_h{horizon}"):
        log_run(
            args.model, dataset_name, horizon, args.min_train_size,
            metrics_df, cost_metrics, n_series, tags,
        )

    print(f"Done. Runtime: {cost_metrics['runtime_sec']:.1f}s")
    print(f"  MAE_mean:   {metrics_df['MAE'].mean():.4f}")
    print(f"  sMAPE_mean: {metrics_df['sMAPE'].mean():.2f}")
    print(f"  WAPE_mean:  {metrics_df['WAPE'].mean():.4f}")
    print(f"  Cost: ${cost_metrics['cost_usd']:.4f}")
    print(f"  CO2:  {cost_metrics['co2_kg']:.6f} kg")


if __name__ == "__main__":
    main()
