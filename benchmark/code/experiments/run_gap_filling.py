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
from evaluation.wrmsse import compute_m5_wrmsse
from models.baselines.seasonal_naive import seasonal_naive_forecast


def load_dataset(dataset: str, task: str = None, **kwargs):
    """Load dataset by name. Returns (df, metadata)."""
    if dataset == "m5":
        sales_path = kwargs.get("sales_path") or os.environ.get(
            "M5_SALES_PATH", "data/m5/sales_train_validation.csv"
        )
        calendar_path = kwargs.get("calendar_path") or os.environ.get(
            "M5_CALENDAR_PATH", "data/m5/calendar.csv"
        )
        prices_path = kwargs.get("prices_path") or os.environ.get(
            "M5_PRICES_PATH"
        )
        with_covariates = kwargs.get("with_covariates", False)
        if with_covariates and not prices_path:
            raise ValueError("with_covariates=True requires prices_path")

        df = load_m5(
            sales_path, calendar_path,
            path_prices=prices_path,
            with_covariates=with_covariates,
        )
        meta = {"dataset": "m5", "horizon": kwargs.get("horizon", 7)}
        if with_covariates:
            from data.loaders.m5 import KNOWN_DYNAMIC_COLUMNS
            meta["known_dynamic_columns"] = KNOWN_DYNAMIC_COLUMNS
        return df, meta

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

    elif dataset == "favorita":
        from data.loaders.favorita import load_favorita, KNOWN_DYNAMIC_COLUMNS
        with_covariates = kwargs.get("with_covariates", False)
        df = load_favorita(
            path_train=kwargs.get("sales_path") or os.environ["FAVORITA_TRAIN_PATH"],
            path_oil=kwargs.get("oil_path") or os.environ.get("FAVORITA_OIL_PATH"),
            path_holidays=kwargs.get("holidays_path") or os.environ.get("FAVORITA_HOLIDAYS_PATH"),
            path_stores=kwargs.get("stores_path") or os.environ.get("FAVORITA_STORES_PATH"),
            path_transactions=kwargs.get("transactions_path") or os.environ.get("FAVORITA_TX_PATH"),
            with_covariates=with_covariates,
            max_series=kwargs.get("max_series"),
        )
        meta = {"dataset": "favorita", "horizon": kwargs.get("horizon", 14)}
        if with_covariates:
            meta["known_dynamic_columns"] = KNOWN_DYNAMIC_COLUMNS
        return df, meta

    elif dataset == "rohlik":
        from data.loaders.rohlik import load_rohlik, KNOWN_DYNAMIC_COLUMNS
        with_covariates = kwargs.get("with_covariates", False)
        df = load_rohlik(
            path_train=kwargs.get("sales_path") or os.environ["ROHLIK_TRAIN_PATH"],
            path_calendar=kwargs.get("calendar_path") or os.environ.get("ROHLIK_CALENDAR_PATH"),
            with_covariates=with_covariates,
            max_series=kwargs.get("max_series"),
        )
        meta = {"dataset": "rohlik", "horizon": kwargs.get("horizon", 14)}
        if with_covariates:
            meta["known_dynamic_columns"] = KNOWN_DYNAMIC_COLUMNS
        return df, meta

    else:
        raise ValueError(f"Unknown dataset: {dataset}")


def _device_for_hardware(hardware: str) -> str:
    """Map hardware name to torch device string."""
    gpu_hardware = {"NC6", "T4", "K80", "A100"}
    return "cuda" if hardware in gpu_hardware else "cpu"


def get_model_fn(model_name: str, hardware: str = "E4DS_V4"):
    """Return (forecast_fn, is_foundation_model) for a given model name."""
    device = _device_for_hardware(hardware)

    if model_name == "seasonal_naive":
        return seasonal_naive_forecast, False

    elif model_name == "chronos2":
        from models.foundation.chronos2 import Chronos2Forecaster
        forecaster = Chronos2Forecaster(device=device)
        return forecaster.predict, True

    elif model_name == "timesfm25":
        from models.foundation.timesfm25 import TimesFM25Forecaster
        forecaster = TimesFM25Forecaster()
        return forecaster.predict, True

    elif model_name == "moirai2":
        from models.foundation.moirai2 import Moirai2Forecaster
        forecaster = Moirai2Forecaster(device=device)
        return forecaster.predict, True

    elif model_name == "lightgbm_cov":
        # Sentinel — LightGBM with covariates uses a different code path
        return None, False

    elif model_name == "lightgbm_direct":
        # Sentinel — direct (non-recursive) LightGBM, separate code path
        return None, False

    else:
        raise ValueError(f"Unknown model: {model_name}")


def _evaluate_lightgbm_cov(
    df, horizon, min_train_size, metadata,
    train_fraction: float = 0.8,
    train_window_days: int = 365,
):
    """
    Vectorized panel LightGBM with covariates for large datasets (e.g. M5).

    Protocol: single global model, trained ONCE on the last `train_window_days`
    of the training portion (first `train_fraction` of days), then recursive
    rolling-origin forecasts in non-overlapping windows of length `horizon`
    over the remaining tail.

    Parameters
    ----------
    df : pd.DataFrame
        Long-format with [series_id, ds, y, ...covariate_cols].
    horizon, min_train_size : int
        min_train_size is ignored when train_fraction is set.
    metadata : dict
        Must contain "known_dynamic_columns" with the covariate names.
    train_fraction : float
        Fraction of days assigned to training. The remainder is the eval tail.
    train_window_days : int
        Cap on training-history depth (last K days of the training portion).
    """
    from lightgbm import LGBMRegressor

    covariate_cols = list(metadata.get("known_dynamic_columns", []))

    df = df.sort_values(["series_id", "ds"]).reset_index(drop=True)
    series_ids = df["series_id"].unique()
    dates = np.sort(df["ds"].unique())
    n_series = len(series_ids)
    n_days = len(dates)

    print(f"  Pivoting to wide ({n_series} series x {n_days} days)...")
    y_wide = df.pivot(index="series_id", columns="ds", values="y") \
                .reindex(series_ids).fillna(0).values.astype(np.float32)
    cov_wide = {}
    for col in covariate_cols:
        cov_wide[col] = (
            df.pivot(index="series_id", columns="ds", values=col)
              .reindex(series_ids).fillna(0).values.astype(np.float32)
        )

    LAGS = (1, 7, 14)
    WINDOWS = (7, 14)
    max_lag = max(max(LAGS), max(WINDOWS))

    train_until = int(n_days * train_fraction)
    train_start = max(max_lag, train_until - train_window_days)
    if train_until - train_start < max_lag + 1:
        raise ValueError(
            f"Not enough training days: train_until={train_until}, "
            f"train_start={train_start}, need >{max_lag}"
        )

    feature_names = (
        [f"lag_{l}" for l in LAGS]
        + [f"roll_mean_{w}" for w in WINDOWS]
        + ["dayofweek"]
        + covariate_cols
    )
    n_features = len(feature_names)

    dayofweek = pd.to_datetime(dates).dayofweek.values.astype(np.int8)

    def features_at(t, y_buf):
        """Build (n_series, n_features) feature matrix using y_buf[:, :t]."""
        cols = []
        for lag in LAGS:
            cols.append(y_buf[:, t - lag])
        for w in WINDOWS:
            cols.append(y_buf[:, t - w : t].mean(axis=1))
        cols.append(np.full(n_series, dayofweek[t], dtype=np.float32))
        for cname in covariate_cols:
            cols.append(cov_wide[cname][:, t])
        return np.column_stack(cols).astype(np.float32, copy=False)

    print(f"  Building training matrix [t={train_start}..{train_until})...")
    n_train_t = train_until - train_start
    X_train = np.empty((n_series * n_train_t, n_features), dtype=np.float32)
    y_train = np.empty(n_series * n_train_t, dtype=np.float32)

    for i, t in enumerate(range(train_start, train_until)):
        rs = i * n_series
        re = rs + n_series
        X_train[rs:re] = features_at(t, y_wide)
        y_train[rs:re] = y_wide[:, t]

    print(f"  Training LightGBM on {len(y_train):,} examples x "
          f"{n_features} features...")
    lgbm = LGBMRegressor(
        objective="tweedie",
        tweedie_variance_power=1.1,
        learning_rate=0.05,
        num_leaves=63,
        n_estimators=300,
        min_child_samples=20,
        verbosity=-1,
    )
    lgbm.fit(X_train, y_train)
    del X_train, y_train

    print(f"  Rolling-origin eval [t={train_until}..{n_days}), horizon={horizon}...")
    eval_starts = list(range(train_until, n_days - horizon + 1, horizon))
    n_eval_days = len(eval_starts) * horizon

    y_pred_wide_eval = np.empty((n_series, n_eval_days), dtype=np.float32)
    eval_t_arr = np.empty(n_eval_days, dtype=np.int32)

    y_buf = y_wide.copy()
    idx = 0
    for t0 in eval_starts:
        for k in range(horizon):
            t = t0 + k
            X_step = features_at(t, y_buf)
            pred = lgbm.predict(X_step).astype(np.float32)
            pred = np.maximum(pred, 0.0)
            y_buf[:, t] = pred
            y_pred_wide_eval[:, idx] = pred
            eval_t_arr[idx] = t
            idx += 1
        y_buf[:, t0 : t0 + horizon] = y_wide[:, t0 : t0 + horizon]

    y_true_wide_eval = y_wide[:, eval_t_arr]
    sid_col = np.repeat(series_ids, n_eval_days)
    y_true_col = y_true_wide_eval.flatten()
    y_pred_col = y_pred_wide_eval.flatten()

    return pd.DataFrame({
        "series_id": sid_col,
        "y_true": y_true_col,
        "y_pred": y_pred_col,
    })


def _evaluate_lightgbm_direct(
    df, horizon, min_train_size, metadata,
    train_fraction: float = 0.8,
    train_window_days: int = 365,
):
    """
    Direct (non-recursive) panel LightGBM with covariates.

    Trains `horizon` separate models, one per offset k in [0, horizon).
    Model k predicts y[t+k] given features built from real history up to
    y[t-1] plus future-known covariates at time t+k. At eval time no model
    output is fed back as input — each step is predicted independently
    from real lags, eliminating the recursive error compounding that hurts
    `lightgbm_cov` at long horizons.

    Same training window protocol as `_evaluate_lightgbm_cov`: single
    fit on the last `train_window_days` of the training portion, then
    rolling-origin tail eval in non-overlapping windows of length `horizon`.
    """
    from lightgbm import LGBMRegressor

    covariate_cols = list(metadata.get("known_dynamic_columns", []))

    df = df.sort_values(["series_id", "ds"]).reset_index(drop=True)
    series_ids = df["series_id"].unique()
    dates = np.sort(df["ds"].unique())
    n_series = len(series_ids)
    n_days = len(dates)

    print(f"  Pivoting to wide ({n_series} series x {n_days} days)...")
    y_wide = df.pivot(index="series_id", columns="ds", values="y") \
                .reindex(series_ids).fillna(0).values.astype(np.float32)
    cov_wide = {}
    for col in covariate_cols:
        cov_wide[col] = (
            df.pivot(index="series_id", columns="ds", values=col)
              .reindex(series_ids).fillna(0).values.astype(np.float32)
        )

    LAGS = (1, 7, 14)
    WINDOWS = (7, 14)
    max_lag = max(max(LAGS), max(WINDOWS))

    train_until = int(n_days * train_fraction)
    train_start = max(max_lag, train_until - train_window_days)
    if train_until - train_start < max_lag + horizon + 1:
        raise ValueError(
            f"Not enough training days for direct h={horizon}: "
            f"train_until={train_until}, train_start={train_start}"
        )

    feature_names = (
        [f"lag_{l}" for l in LAGS]
        + [f"roll_mean_{w}" for w in WINDOWS]
        + ["dayofweek_step"]
        + [f"{c}_step" for c in covariate_cols]
    )
    n_features = len(feature_names)

    dayofweek = pd.to_datetime(dates).dayofweek.values.astype(np.int8)

    def features_at_step(t, k, y_buf):
        """Features for predicting y[t+k] from history up to y[t-1]."""
        cols = []
        for lag in LAGS:
            cols.append(y_buf[:, t - lag])
        for w in WINDOWS:
            cols.append(y_buf[:, t - w : t].mean(axis=1))
        cols.append(np.full(n_series, dayofweek[t + k], dtype=np.float32))
        for cname in covariate_cols:
            cols.append(cov_wide[cname][:, t + k])
        return np.column_stack(cols).astype(np.float32, copy=False)

    models = []
    for k in range(horizon):
        t_max = train_until - k
        n_t = t_max - train_start
        print(f"  [step k={k}] building training matrix ({n_series * n_t:,} rows)...")
        X_k = np.empty((n_series * n_t, n_features), dtype=np.float32)
        y_k = np.empty(n_series * n_t, dtype=np.float32)
        for i, t in enumerate(range(train_start, t_max)):
            rs = i * n_series
            re = rs + n_series
            X_k[rs:re] = features_at_step(t, k, y_wide)
            y_k[rs:re] = y_wide[:, t + k]

        print(f"  [step k={k}] training LightGBM...")
        lgbm = LGBMRegressor(
            objective="tweedie",
            tweedie_variance_power=1.1,
            learning_rate=0.05,
            num_leaves=63,
            n_estimators=300,
            min_child_samples=20,
            verbosity=-1,
        )
        lgbm.fit(X_k, y_k)
        models.append(lgbm)
        del X_k, y_k

    print(f"  Direct eval [t={train_until}..{n_days}), horizon={horizon}...")
    eval_starts = list(range(train_until, n_days - horizon + 1, horizon))
    n_eval_days = len(eval_starts) * horizon
    y_pred_wide_eval = np.empty((n_series, n_eval_days), dtype=np.float32)
    eval_t_arr = np.empty(n_eval_days, dtype=np.int32)

    idx = 0
    for t0 in eval_starts:
        for k in range(horizon):
            X_step = features_at_step(t0, k, y_wide)
            pred = models[k].predict(X_step).astype(np.float32)
            pred = np.maximum(pred, 0.0)
            y_pred_wide_eval[:, idx] = pred
            eval_t_arr[idx] = t0 + k
            idx += 1

    y_true_wide_eval = y_wide[:, eval_t_arr]
    sid_col = np.repeat(series_ids, n_eval_days)
    y_true_col = y_true_wide_eval.flatten()
    y_pred_col = y_pred_wide_eval.flatten()

    return pd.DataFrame({
        "series_id": sid_col,
        "y_true": y_true_col,
        "y_pred": y_pred_col,
    })


def run_experiment(
    model_name: str,
    df: pd.DataFrame,
    horizon: int,
    min_train_size: int,
    hardware: str,
    max_series: int = None,
    metadata: dict = None,
    train_fraction: float = 0.8,
    train_window_days: int = 365,
    wrmsse_paths: dict = None,
):
    """Run a single model on a dataset with cost tracking.

    wrmsse_paths : optional dict with keys sales_path, calendar_path,
        prices_path, train_until. When provided (M5 only), the full 12-level
        WRMSSE is computed and returned alongside the standard metrics.
    """
    if max_series:
        series_ids = df["series_id"].unique()[:max_series]
        df = df[df["series_id"].isin(series_ids)]

    n_series = df["series_id"].nunique()
    n_days_full = df["ds"].nunique()

    tracker = CostTracker(hardware=hardware)
    tracker.start()

    if model_name == "lightgbm_cov":
        results = _evaluate_lightgbm_cov(
            df, horizon, min_train_size, metadata or {},
            train_fraction=train_fraction,
            train_window_days=train_window_days,
        )
        eval_train_until = int(n_days_full * train_fraction)
    elif model_name == "lightgbm_direct":
        results = _evaluate_lightgbm_direct(
            df, horizon, min_train_size, metadata or {},
            train_fraction=train_fraction,
            train_window_days=train_window_days,
        )
        eval_train_until = int(n_days_full * train_fraction)
    else:
        forecast_fn, is_gpu = get_model_fn(model_name, hardware)
        results = rolling_forecast(df, horizon, min_train_size, forecast_fn)
        eval_train_until = min_train_size

    tracker.stop()

    metrics_df = aggregate_metrics(results)
    cost_metrics = tracker.to_dict(n_series=n_series)

    wrmsse_result = None
    if wrmsse_paths and not max_series:
        try:
            wrmsse_result = compute_m5_wrmsse(
                results,
                sales_path=wrmsse_paths["sales_path"],
                calendar_path=wrmsse_paths["calendar_path"],
                prices_path=wrmsse_paths["prices_path"],
                train_until=eval_train_until,
            )
            print(f"  WRMSSE: {wrmsse_result['WRMSSE']:.4f}")
        except Exception as e:
            print(f"WARNING: WRMSSE computation failed: {e}")

    return metrics_df, cost_metrics, n_series, wrmsse_result


def log_run(
    model_name: str,
    dataset_name: str,
    horizon: int,
    min_train_size: int,
    metrics_df: pd.DataFrame,
    cost_metrics: dict,
    n_series: int,
    tags: dict,
    wrmsse_result: dict = None,
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
        wape_mean = metrics_df["WAPE"].dropna().mean()
        if pd.notna(wape_mean):
            mlflow.log_metric("WAPE_mean", wape_mean)
        mlflow.log_metric("WAPE_n_valid", int(metrics_df["WAPE"].notna().sum()))

        mlflow.log_metric("runtime_sec", cost_metrics["runtime_sec"])
        mlflow.log_metric("cost_usd", cost_metrics["cost_usd"])
        mlflow.log_metric("co2_kg", cost_metrics["co2_kg"])
        mlflow.log_metric("series_per_second", cost_metrics["series_per_second"])

        if wrmsse_result is not None:
            mlflow.log_metric("WRMSSE", wrmsse_result["WRMSSE"])
            for li, score in wrmsse_result["level_scores"].items():
                mlflow.log_metric(f"WRMSSE_level{li}", score)
                mlflow.log_metric(
                    f"WRMSSE_level{li}_n_series",
                    wrmsse_result["level_n_series"][li],
                )

        for key, value in tags.items():
            mlflow.set_tag(key, value)
        mlflow.set_tag("hardware", cost_metrics["hardware"])

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "per_series_metrics.csv")
            metrics_df.to_csv(csv_path, index=False)
            try:
                mlflow.log_artifact(csv_path)
            except TypeError:
                # azureml-mlflow artifact builder incompatibility with newer mlflow
                print("WARNING: mlflow.log_artifact failed (azureml-mlflow compat issue), "
                      "skipping per-series CSV upload. Metrics already logged.")


def main():
    parser = argparse.ArgumentParser(description="Run gap-filling experiment")
    parser.add_argument("--model", required=True,
                        choices=["seasonal_naive", "chronos2", "timesfm25", "moirai2",
                                 "lightgbm_cov", "lightgbm_direct"])
    parser.add_argument("--dataset", required=True,
                        choices=["m5", "gift_eval", "fev_bench", "favorita", "rohlik"])
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
    parser.add_argument("--prices-path", default=None)
    parser.add_argument("--oil-path", default=None)
    parser.add_argument("--holidays-path", default=None)
    parser.add_argument("--stores-path", default=None)
    parser.add_argument("--transactions-path", default=None)
    parser.add_argument("--train-fraction", type=float, default=0.8,
                        help="LightGBM only: fraction of days for training")
    parser.add_argument("--train-window-days", type=int, default=365,
                        help="LightGBM only: cap on training history depth")
    parser.add_argument("--term", default="short", help="GIFT-Eval term")
    args = parser.parse_args()

    with_covariates = args.model in ("lightgbm_cov", "lightgbm_direct")

    print(f"Loading {args.dataset}" + (f"/{args.task}" if args.task else "") + "...")
    df, metadata = load_dataset(
        args.dataset,
        task=args.task,
        sales_path=args.sales_path,
        calendar_path=args.calendar_path,
        prices_path=args.prices_path,
        oil_path=args.oil_path,
        holidays_path=args.holidays_path,
        stores_path=args.stores_path,
        transactions_path=args.transactions_path,
        with_covariates=with_covariates,
        horizon=args.horizon,
        term=args.term,
    )

    horizon = args.horizon or metadata.get("horizon", 7)
    dataset_name = metadata.get("dataset", args.dataset)
    if args.task:
        dataset_name = f"{args.dataset}/{args.task}"

    print(f"Dataset: {df['series_id'].nunique()} series, {len(df)} rows")
    print(f"Running {args.model} with horizon={horizon}...")

    wrmsse_paths = None
    if args.dataset == "m5" and args.sales_path and args.calendar_path and args.prices_path:
        wrmsse_paths = {
            "sales_path": args.sales_path,
            "calendar_path": args.calendar_path,
            "prices_path": args.prices_path,
        }

    metrics_df, cost_metrics, n_series, wrmsse_result = run_experiment(
        args.model, df, horizon, args.min_train_size,
        args.hardware, args.max_series, metadata,
        train_fraction=args.train_fraction,
        train_window_days=args.train_window_days,
        wrmsse_paths=wrmsse_paths,
    )

    tags = {"phase": "gap_filling", "eval_method": "rolling_origin", "paper": "meta-analysis"}
    mlflow.set_experiment("meta-analysis-gap-filling")

    with mlflow.start_run(run_name=f"{dataset_name}_h{horizon}"):
        log_run(
            args.model, dataset_name, horizon, args.min_train_size,
            metrics_df, cost_metrics, n_series, tags,
            wrmsse_result=wrmsse_result,
        )

    print(f"Done. Runtime: {cost_metrics['runtime_sec']:.1f}s")
    print(f"  MAE_mean:   {metrics_df['MAE'].mean():.4f}")
    print(f"  sMAPE_mean: {metrics_df['sMAPE'].mean():.2f}")
    print(f"  WAPE_mean:  {metrics_df['WAPE'].dropna().mean():.4f} "
          f"(n_valid={int(metrics_df['WAPE'].notna().sum())})")
    print(f"  Cost: ${cost_metrics['cost_usd']:.4f}")
    print(f"  CO2:  {cost_metrics['co2_kg']:.6f} kg")
    if wrmsse_result is not None:
        print(f"  WRMSSE: {wrmsse_result['WRMSSE']:.4f}")


if __name__ == "__main__":
    main()
