"""
Rerun Source B on a matched series/origin panel.

This is the repair runner for the v1.3 audit findings.  Unlike the original
gap-filling runner, every model in a dataset-horizon cell is evaluated on the
same series IDs and the same rolling-origin windows, and the script writes
prediction-level outputs that can support paired contrasts.

Example:
    python benchmark/code/experiments/run_source_b_paired_panel.py \
        --datasets m5 rohlik \
        --models seasonal_naive lightgbm_cov lightgbm_direct chronos_bolt_tiny \
        --horizons 7 14 28 \
        --max-series 100
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names, but LGBMRegressor was fitted with feature names",
    category=UserWarning,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "benchmark" / "code"))

from evaluation.cost import CostTracker
from evaluation.metrics import mae, smape, wape
from models.baselines.seasonal_naive import seasonal_naive_forecast


LAGS = (1, 7, 14)
WINDOWS = (7, 14)
BASELINE_MODELS = {
    "seasonal_naive",
    "lightgbm_cov",
    "lightgbm_direct",
    "lightgbm_direct_scaled",
    "lightgbm_tuned_cov",
    "lightgbm_tuned_direct",
}
FM_MODELS = {"chronos_bolt_tiny", "chronos2", "timesfm25", "tirex", "moirai2"}
CONTRAST_COLUMNS = [
    "run_id",
    "panel_id",
    "dataset",
    "horizon",
    "model_name",
    "baseline_model",
    "n_series",
    "model_WAPE_aggregate",
    "baseline_WAPE_aggregate",
    "log_ratio",
    "bootstrap_se",
    "ci95_low",
    "ci95_high",
    "n_boot",
]

DEFAULT_LIGHTGBM_PARAMS = {
    "objective": "tweedie",
    "tweedie_variance_power": 1.1,
    "learning_rate": 0.05,
    "num_leaves": 63,
    "n_estimators": 300,
    "min_child_samples": 20,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "reg_alpha": 0.0,
    "reg_lambda": 0.0,
    "verbosity": -1,
    "random_state": 20260714,
}


@dataclass(frozen=True)
class DatasetBundle:
    name: str
    frame: pd.DataFrame
    covariate_cols: tuple[str, ...]


def _default_paths() -> dict[str, str | None]:
    return {
        "m5_sales": os.environ.get("M5_SALES_PATH", str(REPO_ROOT / "data/raw/m5/sales_train_validation.csv")),
        "m5_calendar": os.environ.get("M5_CALENDAR_PATH", str(REPO_ROOT / "data/raw/m5/calendar.csv")),
        "m5_prices": os.environ.get("M5_PRICES_PATH", str(REPO_ROOT / "data/raw/m5/sell_prices.csv")),
        "favorita_train": os.environ.get("FAVORITA_TRAIN_PATH", str(REPO_ROOT / "data/raw/favorita/train.parquet")),
        "favorita_oil": os.environ.get("FAVORITA_OIL_PATH", str(REPO_ROOT / "data/raw/favorita/oil.csv")),
        "favorita_holidays": os.environ.get("FAVORITA_HOLIDAYS_PATH", str(REPO_ROOT / "data/raw/favorita/holidays_events.csv")),
        "favorita_stores": os.environ.get("FAVORITA_STORES_PATH", str(REPO_ROOT / "data/raw/favorita/stores.csv")),
        "favorita_tx": os.environ.get("FAVORITA_TX_PATH", str(REPO_ROOT / "data/raw/favorita/transactions.csv")),
        "rohlik_train": os.environ.get("ROHLIK_TRAIN_PATH", str(REPO_ROOT / "data/raw/rohlik-v2/sales_train.csv")),
        "rohlik_calendar": os.environ.get("ROHLIK_CALENDAR_PATH", str(REPO_ROOT / "data/raw/rohlik-v2/calendar.csv")),
    }


def load_dataset(name: str) -> DatasetBundle:
    paths = _default_paths()
    if name == "m5":
        from data.loaders.m5 import KNOWN_DYNAMIC_COLUMNS, load_m5

        df = load_m5(
            paths["m5_sales"],
            paths["m5_calendar"],
            path_prices=paths["m5_prices"],
            with_covariates=True,
        )
        return DatasetBundle(name="M5", frame=df, covariate_cols=tuple(KNOWN_DYNAMIC_COLUMNS))
    if name == "favorita":
        from data.loaders.favorita import KNOWN_DYNAMIC_COLUMNS, load_favorita

        df = load_favorita(
            path_train=paths["favorita_train"],
            path_oil=paths["favorita_oil"],
            path_holidays=paths["favorita_holidays"],
            path_stores=paths["favorita_stores"],
            path_transactions=paths["favorita_tx"],
            with_covariates=True,
        )
        return DatasetBundle(name="Favorita", frame=df, covariate_cols=tuple(KNOWN_DYNAMIC_COLUMNS))
    if name == "rohlik":
        from data.loaders.rohlik import KNOWN_DYNAMIC_COLUMNS, load_rohlik

        df = load_rohlik(
            path_train=paths["rohlik_train"],
            path_calendar=paths["rohlik_calendar"],
            with_covariates=True,
        )
        return DatasetBundle(name="Rohlik", frame=df, covariate_cols=tuple(KNOWN_DYNAMIC_COLUMNS))
    raise ValueError(f"Unknown dataset: {name}")


def select_series_ids(df: pd.DataFrame, max_series: int, method: str, seed: int) -> np.ndarray:
    if method == "top_volume":
        return (
            df.groupby("series_id", sort=False)["y"]
            .sum()
            .sort_values(ascending=False)
            .head(max_series)
            .index.to_numpy()
        )
    if method == "random":
        ids = np.array(sorted(df["series_id"].unique()))
        rng = np.random.default_rng(seed)
        if len(ids) <= max_series:
            return ids
        return np.array(sorted(rng.choice(ids, size=max_series, replace=False)))
    if method == "stratified_volume_zero":
        stats = (
            df.groupby("series_id", sort=False)["y"]
            .agg(total_volume="sum", zero_fraction=lambda s: float((s <= 0).mean()))
            .reset_index()
        )
        if len(stats) <= max_series:
            return np.array(sorted(stats["series_id"].astype(str)))

        n_volume_bins = min(4, len(stats))
        stats["volume_bin"] = pd.qcut(
            stats["total_volume"].rank(method="first"),
            q=n_volume_bins,
            labels=False,
            duplicates="drop",
        )
        n_zero_bins = min(4, len(stats))
        stats["zero_bin"] = pd.qcut(
            stats["zero_fraction"].rank(method="first"),
            q=n_zero_bins,
            labels=False,
            duplicates="drop",
        )
        rng = np.random.default_rng(seed)
        selected: list[str] = []
        strata = [
            group
            for _, group in stats.groupby(["volume_bin", "zero_bin"], sort=True)
            if not group.empty
        ]
        base_n = max_series // len(strata)
        remainder = max_series % len(strata)
        for idx, group in enumerate(strata):
            take = min(len(group), base_n + (1 if idx < remainder else 0))
            if take:
                selected.extend(rng.choice(group["series_id"].astype(str), size=take, replace=False))
        if len(selected) < max_series:
            remaining = stats[~stats["series_id"].astype(str).isin(selected)]["series_id"].astype(str)
            selected.extend(rng.choice(remaining.to_numpy(), size=max_series - len(selected), replace=False))
        return np.array(sorted(selected))
    raise ValueError(f"Unknown series selection method: {method}")


def densify_panel(df: pd.DataFrame, series_ids: np.ndarray, covariate_cols: tuple[str, ...]) -> pd.DataFrame:
    """Create one row per selected series-date; missing demand is explicit zero."""
    panel = df[df["series_id"].isin(series_ids)].copy()
    panel["ds"] = pd.to_datetime(panel["ds"])
    dates = pd.Index(sorted(panel["ds"].unique()), name="ds")
    full_index = pd.MultiIndex.from_product([series_ids, dates], names=["series_id", "ds"])

    cols = ["series_id", "ds", "y"] + list(covariate_cols)
    dense = (
        panel[cols]
        .drop_duplicates(["series_id", "ds"], keep="last")
        .set_index(["series_id", "ds"])
        .reindex(full_index)
        .reset_index()
    )
    dense["y"] = dense["y"].fillna(0.0).astype("float32")
    for col in covariate_cols:
        dense[col] = (
            dense.groupby("series_id", sort=False)[col]
            .ffill()
            .bfill()
            .fillna(0.0)
            .astype("float32")
        )
    return dense


def make_wide(dense: pd.DataFrame, covariate_cols: tuple[str, ...]):
    dense = dense.sort_values(["series_id", "ds"]).reset_index(drop=True)
    series_ids = dense["series_id"].drop_duplicates().to_numpy()
    dates = np.array(sorted(dense["ds"].unique()))
    y_wide = (
        dense.pivot(index="series_id", columns="ds", values="y")
        .reindex(index=series_ids, columns=dates)
        .fillna(0.0)
        .to_numpy(dtype=np.float32)
    )
    cov_wide = {}
    for col in covariate_cols:
        cov_wide[col] = (
            dense.pivot(index="series_id", columns="ds", values=col)
            .reindex(index=series_ids, columns=dates)
            .ffill(axis=1)
            .bfill(axis=1)
            .fillna(0.0)
            .to_numpy(dtype=np.float32)
        )
    return series_ids, dates, y_wide, cov_wide


def eval_starts_for(n_days: int, horizon: int, train_fraction: float) -> list[int]:
    train_until = int(n_days * train_fraction)
    min_required = max(max(LAGS), max(WINDOWS), 7)
    if train_until <= min_required:
        raise ValueError(f"train_until={train_until} leaves insufficient history")
    starts = list(range(train_until, n_days - horizon + 1, horizon))
    if not starts:
        raise ValueError(f"No eval starts for n_days={n_days}, horizon={horizon}")
    return starts


def predictions_from_wide(
    series_ids: np.ndarray,
    dates: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    eval_t: np.ndarray,
    origin_t: np.ndarray,
    model_name: str,
    dataset: str,
    horizon: int,
    run_id: str,
    panel_id: str,
) -> pd.DataFrame:
    n_series, n_eval = y_pred.shape
    series_ids = series_ids.astype(str)
    return pd.DataFrame(
        {
            "run_id": run_id,
            "panel_id": panel_id,
            "dataset": dataset,
            "horizon": horizon,
            "model_name": model_name,
            "series_id": np.repeat(series_ids, n_eval),
            "origin_idx": np.tile(origin_t, n_series),
            "origin_ds": np.tile(dates[origin_t], n_series),
            "target_idx": np.tile(eval_t, n_series),
            "ds": np.tile(dates[eval_t], n_series),
            "step": np.tile(eval_t - origin_t + 1, n_series),
            "y_true": y_true.reshape(-1),
            "y_pred": y_pred.reshape(-1),
        }
    )


def evaluate_seasonal_naive(
    y_wide: np.ndarray,
    starts: list[int],
    horizon: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pred_blocks = []
    true_blocks = []
    eval_t = []
    origin_t = []
    for t0 in starts:
        last = y_wide[:, t0 - 7 : t0]
        reps = int(np.ceil(horizon / 7))
        pred = np.tile(last, reps)[:, :horizon]
        pred_blocks.append(pred)
        true_blocks.append(y_wide[:, t0 : t0 + horizon])
        eval_t.extend(range(t0, t0 + horizon))
        origin_t.extend([t0] * horizon)
    return (
        np.concatenate(true_blocks, axis=1),
        np.concatenate(pred_blocks, axis=1),
        np.asarray(eval_t, dtype=np.int32),
        np.asarray(origin_t, dtype=np.int32),
    )


def feature_matrix_at(
    t: int,
    y_buf: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    dayofweek: np.ndarray,
    step_offset: int = 0,
) -> np.ndarray:
    cols = []
    for lag in LAGS:
        cols.append(y_buf[:, t - lag])
    for window in WINDOWS:
        cols.append(y_buf[:, t - window : t].mean(axis=1))
    cov_t = t + step_offset
    cols.append(np.full(y_buf.shape[0], dayofweek[cov_t], dtype=np.float32))
    for col in covariate_cols:
        cols.append(cov_wide[col][:, cov_t])
    return np.column_stack(cols).astype(np.float32, copy=False)


def _lightgbm_params(overrides: dict | None = None, seed: int = 20260714) -> dict:
    params = dict(DEFAULT_LIGHTGBM_PARAMS)
    params["random_state"] = int(seed)
    if overrides:
        params.update(overrides)
    return params


def sample_lightgbm_params(rng: np.random.Generator, trial: int, seed: int) -> dict:
    if trial == 0:
        return _lightgbm_params(seed=seed)
    return _lightgbm_params(
        {
            "learning_rate": float(rng.choice([0.015, 0.025, 0.04, 0.06, 0.08])),
            "num_leaves": int(rng.choice([15, 31, 63, 127])),
            "n_estimators": int(rng.choice([150, 300, 600, 900])),
            "min_child_samples": int(rng.choice([10, 20, 50, 100])),
            "subsample": float(rng.choice([0.7, 0.85, 1.0])),
            "subsample_freq": 1,
            "colsample_bytree": float(rng.choice([0.7, 0.85, 1.0])),
            "reg_alpha": float(rng.choice([0.0, 0.01, 0.1, 1.0])),
            "reg_lambda": float(rng.choice([0.0, 0.1, 1.0, 5.0])),
            "tweedie_variance_power": float(rng.choice([1.05, 1.1, 1.2, 1.4])),
        },
        seed=seed + trial,
    )


def validation_start_for(starts: list[int], horizon: int) -> int:
    validation_start = starts[0] - horizon
    min_required = max(max(LAGS), max(WINDOWS), 7)
    if validation_start <= min_required:
        raise ValueError(
            f"Cannot create validation origin before first eval start={starts[0]} "
            f"for horizon={horizon}"
        )
    return validation_start


def _fit_lightgbm_recursive_model(
    y_wide: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    dates: np.ndarray,
    train_until: int,
    train_window_days: int,
    params: dict,
):
    from lightgbm import LGBMRegressor

    train_start = max(max(max(LAGS), max(WINDOWS)), train_until - train_window_days)
    dayofweek = pd.to_datetime(dates).dayofweek.to_numpy(dtype=np.int8)
    train_times = list(range(train_start, train_until))
    x_train = np.vstack([
        feature_matrix_at(t, y_wide, cov_wide, covariate_cols, dayofweek)
        for t in train_times
    ])
    y_train = np.concatenate([y_wide[:, t] for t in train_times])
    model = LGBMRegressor(**params)
    model.fit(x_train, y_train)
    return model


def _predict_lightgbm_recursive_block(
    model,
    y_wide: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    dates: np.ndarray,
    t0: int,
    horizon: int,
) -> np.ndarray:
    n_series = y_wide.shape[0]
    dayofweek = pd.to_datetime(dates).dayofweek.to_numpy(dtype=np.int8)
    y_buf = y_wide.copy()
    block = np.empty((n_series, horizon), dtype=np.float32)
    for k in range(horizon):
        t = t0 + k
        x_step = feature_matrix_at(t, y_buf, cov_wide, covariate_cols, dayofweek)
        pred = np.maximum(model.predict(x_step).astype(np.float32), 0.0)
        y_buf[:, t] = pred
        block[:, k] = pred
    return block


def _fit_lightgbm_direct_models(
    y_wide: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    dates: np.ndarray,
    train_until: int,
    horizon: int,
    train_window_days: int,
    params: dict,
) -> list:
    from lightgbm import LGBMRegressor

    train_start = max(max(max(LAGS), max(WINDOWS)), train_until - train_window_days)
    dayofweek = pd.to_datetime(dates).dayofweek.to_numpy(dtype=np.int8)
    models = []
    for k in range(horizon):
        train_times = list(range(train_start, train_until - k))
        x_train = np.vstack([
            feature_matrix_at(t, y_wide, cov_wide, covariate_cols, dayofweek, step_offset=k)
            for t in train_times
        ])
        y_train = np.concatenate([y_wide[:, t + k] for t in train_times])
        model = LGBMRegressor(**params)
        model.fit(x_train, y_train)
        models.append(model)
    return models


def _predict_lightgbm_direct_block(
    models: list,
    y_wide: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    dates: np.ndarray,
    t0: int,
    horizon: int,
) -> np.ndarray:
    n_series = y_wide.shape[0]
    dayofweek = pd.to_datetime(dates).dayofweek.to_numpy(dtype=np.int8)
    block = np.empty((n_series, horizon), dtype=np.float32)
    for k, model in enumerate(models):
        x_step = feature_matrix_at(t0, y_wide, cov_wide, covariate_cols, dayofweek, step_offset=k)
        block[:, k] = np.maximum(model.predict(x_step).astype(np.float32), 0.0)
    return block


def tune_lightgbm_params(
    protocol: str,
    y_wide: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    dates: np.ndarray,
    starts: list[int],
    horizon: int,
    train_window_days: int,
    n_trials: int,
    seed: int,
    checkpoint_path: Path | None = None,
) -> tuple[dict, pd.DataFrame]:
    """Tune LightGBM on the origin immediately before the evaluation panel."""
    if n_trials <= 0:
        return _lightgbm_params(seed=seed), pd.DataFrame()

    val_start = validation_start_for(starts, horizon)
    rng = np.random.default_rng(seed)
    rows = []
    completed_trials: set[int] = set()
    if checkpoint_path is not None and checkpoint_path.exists():
        checkpoint = pd.read_csv(checkpoint_path)
        if not checkpoint.empty:
            rows.extend(checkpoint.to_dict("records"))
            completed_trials = set(checkpoint["trial"].astype(int).tolist())
            print(
                f"Resuming {protocol} tuning from {checkpoint_path}: "
                f"{len(completed_trials)}/{n_trials} trials complete",
                flush=True,
            )
    best_score = np.inf
    best_params = None
    for row in rows:
        score = float(row["validation_WAPE_aggregate"])
        if np.isfinite(score) and score < best_score:
            best_score = score
            best_params = json.loads(row["params_json"])
    for trial in range(n_trials):
        params = sample_lightgbm_params(rng, trial, seed)
        if trial in completed_trials:
            continue
        if protocol == "recursive":
            model = _fit_lightgbm_recursive_model(
                y_wide, cov_wide, covariate_cols, dates, val_start, train_window_days, params
            )
            pred = _predict_lightgbm_recursive_block(
                model, y_wide, cov_wide, covariate_cols, dates, val_start, horizon
            )
        elif protocol == "direct":
            models = _fit_lightgbm_direct_models(
                y_wide, cov_wide, covariate_cols, dates, val_start, horizon, train_window_days, params
            )
            pred = _predict_lightgbm_direct_block(
                models, y_wide, cov_wide, covariate_cols, dates, val_start, horizon
            )
        else:
            raise ValueError(f"Unknown LightGBM protocol: {protocol}")
        truth = y_wide[:, val_start : val_start + horizon]
        score = wape(truth.reshape(-1), pred.reshape(-1))
        row = {
            "trial": trial,
            "protocol": protocol,
            "validation_start_idx": val_start,
            "validation_horizon": horizon,
            "validation_WAPE_aggregate": float(score),
            "params_json": json.dumps(params, sort_keys=True),
        }
        rows.append(row)
        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).sort_values(["trial"]).to_csv(checkpoint_path, index=False)
        if np.isfinite(score) and score < best_score:
            best_score = float(score)
            best_params = params
    trials = pd.DataFrame(rows)
    if best_params is None:
        best_params = _lightgbm_params(seed=seed)
    return best_params, trials


def evaluate_lightgbm_recursive(
    y_wide: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    dates: np.ndarray,
    starts: list[int],
    horizon: int,
    train_window_days: int,
    params: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_series, _ = y_wide.shape
    train_until = starts[0]
    model = _fit_lightgbm_recursive_model(
        y_wide,
        cov_wide,
        covariate_cols,
        dates,
        train_until,
        train_window_days,
        params or _lightgbm_params(),
    )

    pred_blocks = []
    true_blocks = []
    eval_t = []
    origin_t = []
    for t0 in starts:
        block = _predict_lightgbm_recursive_block(
            model, y_wide, cov_wide, covariate_cols, dates, t0, horizon
        )
        pred_blocks.append(block)
        true_blocks.append(y_wide[:, t0 : t0 + horizon])
        eval_t.extend(range(t0, t0 + horizon))
        origin_t.extend([t0] * horizon)
    return (
        np.concatenate(true_blocks, axis=1),
        np.concatenate(pred_blocks, axis=1),
        np.asarray(eval_t, dtype=np.int32),
        np.asarray(origin_t, dtype=np.int32),
    )


def evaluate_lightgbm_direct(
    y_wide: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    dates: np.ndarray,
    starts: list[int],
    horizon: int,
    train_window_days: int,
    params: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_series, _ = y_wide.shape
    train_until = starts[0]
    models = _fit_lightgbm_direct_models(
        y_wide,
        cov_wide,
        covariate_cols,
        dates,
        train_until,
        horizon,
        train_window_days,
        params or _lightgbm_params(),
    )

    pred_blocks = []
    true_blocks = []
    eval_t = []
    origin_t = []
    for t0 in starts:
        block = _predict_lightgbm_direct_block(
            models, y_wide, cov_wide, covariate_cols, dates, t0, horizon
        )
        pred_blocks.append(block)
        true_blocks.append(y_wide[:, t0 : t0 + horizon])
        eval_t.extend(range(t0, t0 + horizon))
        origin_t.extend([t0] * horizon)
    return (
        np.concatenate(true_blocks, axis=1),
        np.concatenate(pred_blocks, axis=1),
        np.asarray(eval_t, dtype=np.int32),
        np.asarray(origin_t, dtype=np.int32),
    )


def get_fm_predictor(model_name: str, hardware: str) -> Callable[[pd.Series, int], pd.Series]:
    device = "mps" if hardware == "M_SERIES_MAC" else ("cuda" if hardware in {"NC6", "T4", "K80", "A100"} else "cpu")
    if model_name == "chronos_bolt_tiny":
        from models.foundation.chronos_bolt_tiny import ChronosBoltTinyForecaster

        return ChronosBoltTinyForecaster(device=device).predict
    if model_name == "chronos2":
        from models.foundation.chronos2 import Chronos2Forecaster

        return Chronos2Forecaster(device=device).predict
    if model_name == "timesfm25":
        from models.foundation.timesfm25 import TimesFM25Forecaster

        return TimesFM25Forecaster(device="cpu").predict
    if model_name == "tirex":
        from models.foundation.tirex import TiRexForecaster

        return TiRexForecaster(device=device).predict
    if model_name == "moirai2":
        from models.foundation.moirai2 import Moirai2Forecaster

        return Moirai2Forecaster(device=device).predict
    raise ValueError(f"Unknown FM model: {model_name}")


def fm_device_for(hardware: str) -> str:
    return "mps" if hardware == "M_SERIES_MAC" else ("cuda" if hardware in {"NC6", "T4", "K80", "A100"} else "cpu")


def tirex_device_for(hardware: str) -> str:
    if hardware == "M_SERIES_MAC":
        return "cpu"
    return fm_device_for(hardware)


def evaluate_fm(
    y_wide: np.ndarray,
    starts: list[int],
    horizon: int,
    predict_fn: Callable[[pd.Series, int], pd.Series],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_series = y_wide.shape[0]
    n_eval = len(starts) * horizon
    y_true = np.empty((n_series, n_eval), dtype=np.float32)
    y_pred = np.empty((n_series, n_eval), dtype=np.float32)
    eval_t = []
    origin_t = []
    col = 0
    for t0 in starts:
        for i in range(n_series):
            train = pd.Series(y_wide[i, :t0])
            pred = np.asarray(predict_fn(train, horizon), dtype=np.float32)[:horizon]
            if len(pred) < horizon:
                pred = np.pad(pred, (0, horizon - len(pred)), constant_values=np.nan)
            y_pred[i, col : col + horizon] = pred
            y_true[i, col : col + horizon] = y_wide[i, t0 : t0 + horizon]
        eval_t.extend(range(t0, t0 + horizon))
        origin_t.extend([t0] * horizon)
        col += horizon
    return y_true, y_pred, np.asarray(eval_t, dtype=np.int32), np.asarray(origin_t, dtype=np.int32)


def evaluate_fm_batch(
    y_wide: np.ndarray,
    starts: list[int],
    horizon: int,
    forecaster,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_series = y_wide.shape[0]
    n_eval = len(starts) * horizon
    y_true = np.empty((n_series, n_eval), dtype=np.float32)
    y_pred = np.empty((n_series, n_eval), dtype=np.float32)
    eval_t = []
    origin_t = []
    col = 0
    for t0 in starts:
        histories = [y_wide[i, :t0] for i in range(n_series)]
        pred = np.asarray(forecaster.predict_batch(histories, horizon), dtype=np.float32)
        if pred.shape[1] < horizon:
            pad = np.full((n_series, horizon - pred.shape[1]), np.nan, dtype=np.float32)
            pred = np.column_stack([pred, pad])
        y_pred[:, col : col + horizon] = pred[:, :horizon]
        y_true[:, col : col + horizon] = y_wide[:, t0 : t0 + horizon]
        eval_t.extend(range(t0, t0 + horizon))
        origin_t.extend([t0] * horizon)
        col += horizon
    return y_true, y_pred, np.asarray(eval_t, dtype=np.int32), np.asarray(origin_t, dtype=np.int32)


def per_series_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["run_id", "panel_id", "dataset", "horizon", "model_name", "series_id"]
    for keys, g in predictions.groupby(group_cols, sort=False):
        y_t = g["y_true"].to_numpy(dtype=float)
        y_p = g["y_pred"].to_numpy(dtype=float)
        valid = np.isfinite(y_t) & np.isfinite(y_p)
        y_t = y_t[valid]
        y_p = y_p[valid]
        abs_y = float(np.abs(y_t).sum())
        abs_error = float(np.abs(y_t - y_p).sum())
        rows.append(
            dict(
                zip(group_cols, keys),
                n_predictions=int(len(y_t)),
                abs_y=abs_y,
                abs_error=abs_error,
                MAE=mae(y_t, y_p) if len(y_t) else np.nan,
                sMAPE=smape(y_t, y_p) if len(y_t) else np.nan,
                WAPE=wape(y_t, y_p) if len(y_t) else np.nan,
            )
        )
    return pd.DataFrame(rows)


def cell_summary(
    metrics: pd.DataFrame,
    run_meta: list[dict],
) -> pd.DataFrame:
    summary = (
        metrics.groupby(["run_id", "panel_id", "dataset", "horizon", "model_name"], sort=False)
        .agg(
            n_series=("series_id", "nunique"),
            n_valid_wape=("WAPE", lambda x: int(x.notna().sum())),
            n_predictions=("n_predictions", "sum"),
            abs_y=("abs_y", "sum"),
            abs_error=("abs_error", "sum"),
            WAPE_mean=("WAPE", "mean"),
            MAE_mean=("MAE", "mean"),
            sMAPE_mean=("sMAPE", "mean"),
        )
        .reset_index()
    )
    summary["WAPE_aggregate"] = summary["abs_error"] / summary["abs_y"].replace(0, np.nan)
    return summary.merge(pd.DataFrame(run_meta), on=["run_id", "panel_id", "dataset", "horizon", "model_name"], how="left")


def paired_bootstrap(
    metrics: pd.DataFrame,
    summary: pd.DataFrame,
    n_boot: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    key_cols = ["run_id", "panel_id", "dataset", "horizon"]
    for keys, g in metrics.groupby(key_cols, sort=False):
        cell_summary_df = summary
        for key_col, key_value in zip(key_cols, keys):
            cell_summary_df = cell_summary_df[cell_summary_df[key_col] == key_value]
        baselines = cell_summary_df[cell_summary_df["model_name"].isin(BASELINE_MODELS)]
        if baselines.empty:
            continue
        best_baseline = baselines.sort_values("WAPE_aggregate").iloc[0]["model_name"]
        models = sorted(set(g["model_name"]) - {best_baseline})
        for model_name in models:
            if model_name in BASELINE_MODELS:
                continue
            wide = g[g["model_name"].isin([model_name, best_baseline])].pivot(
                index="series_id",
                columns="model_name",
                values=["abs_error", "abs_y"],
            )
            if ("abs_error", model_name) not in wide or ("abs_error", best_baseline) not in wide:
                continue
            wide = wide.dropna()
            if wide.empty:
                continue
            model_err = wide[("abs_error", model_name)].to_numpy(float)
            model_y = wide[("abs_y", model_name)].to_numpy(float)
            base_err = wide[("abs_error", best_baseline)].to_numpy(float)
            base_y = wide[("abs_y", best_baseline)].to_numpy(float)
            model_wape = model_err.sum() / model_y.sum()
            base_wape = base_err.sum() / base_y.sum()
            log_ratio = float(np.log(model_wape / base_wape))
            boot = []
            n = len(wide)
            for _ in range(n_boot):
                idx = rng.integers(0, n, size=n)
                mw = model_err[idx].sum() / model_y[idx].sum()
                bw = base_err[idx].sum() / base_y[idx].sum()
                if mw > 0 and bw > 0 and np.isfinite(mw) and np.isfinite(bw):
                    boot.append(np.log(mw / bw))
            boot_arr = np.asarray(boot)
            rows.append(
                {
                    **dict(zip(key_cols, keys)),
                    "model_name": model_name,
                    "baseline_model": best_baseline,
                    "n_series": n,
                    "model_WAPE_aggregate": model_wape,
                    "baseline_WAPE_aggregate": base_wape,
                    "log_ratio": log_ratio,
                    "bootstrap_se": float(np.std(boot_arr, ddof=1)) if len(boot_arr) > 1 else np.nan,
                    "ci95_low": float(np.quantile(boot_arr, 0.025)) if len(boot_arr) else np.nan,
                    "ci95_high": float(np.quantile(boot_arr, 0.975)) if len(boot_arr) else np.nan,
                    "n_boot": int(len(boot_arr)),
                }
            )
    return pd.DataFrame(rows, columns=CONTRAST_COLUMNS)


def run_cell(
    model_name: str,
    dataset: str,
    horizon: int,
    series_ids: np.ndarray,
    dates: np.ndarray,
    y_wide: np.ndarray,
    cov_wide: dict[str, np.ndarray],
    covariate_cols: tuple[str, ...],
    starts: list[int],
    args: argparse.Namespace,
    run_id: str,
    panel_id: str,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    print(f"[{dataset} h={horizon}] {model_name}: {len(series_ids)} series, {len(starts)} origins", flush=True)
    tracker = CostTracker(args.hardware)
    start_time = time.time()
    tracker.start()
    if model_name == "seasonal_naive":
        y_true, y_pred, eval_t, origin_t = evaluate_seasonal_naive(y_wide, starts, horizon)
        model_params = {}
        tuning_trials = pd.DataFrame()
    elif model_name == "lightgbm_cov":
        y_true, y_pred, eval_t, origin_t = evaluate_lightgbm_recursive(
            y_wide,
            cov_wide,
            covariate_cols,
            dates,
            starts,
            horizon,
            args.train_window_days,
            params=_lightgbm_params(seed=args.seed),
        )
        model_params = {"n_estimators": 300, "protocol": "recursive"}
        tuning_trials = pd.DataFrame()
    elif model_name == "lightgbm_tuned_cov":
        checkpoint_path = (
            Path(args.out_dir)
            / run_id
            / f"tuning_trials_{dataset.lower()}_h{horizon}_{model_name}.csv"
        )
        tuned_params, tuning_trials = tune_lightgbm_params(
            "recursive",
            y_wide,
            cov_wide,
            covariate_cols,
            dates,
            starts,
            horizon,
            args.train_window_days,
            args.lightgbm_tuning_trials,
            args.seed + horizon,
            checkpoint_path=checkpoint_path,
        )
        y_true, y_pred, eval_t, origin_t = evaluate_lightgbm_recursive(
            y_wide,
            cov_wide,
            covariate_cols,
            dates,
            starts,
            horizon,
            args.train_window_days,
            params=tuned_params,
        )
        model_params = {
            "protocol": "recursive_tuned",
            "tuning_trials": args.lightgbm_tuning_trials,
            "selected_params": tuned_params,
        }
    elif model_name == "lightgbm_direct":
        y_true, y_pred, eval_t, origin_t = evaluate_lightgbm_direct(
            y_wide,
            cov_wide,
            covariate_cols,
            dates,
            starts,
            horizon,
            args.train_window_days,
            params=_lightgbm_params(seed=args.seed),
        )
        model_params = {"n_estimators_per_head": 300, "protocol": "direct"}
        tuning_trials = pd.DataFrame()
    elif model_name == "lightgbm_direct_scaled":
        n_estimators = int(300 * horizon / 7)
        y_true, y_pred, eval_t, origin_t = evaluate_lightgbm_direct(
            y_wide,
            cov_wide,
            covariate_cols,
            dates,
            starts,
            horizon,
            args.train_window_days,
            params=_lightgbm_params({"n_estimators": n_estimators}, seed=args.seed),
        )
        model_params = {"n_estimators_per_head": n_estimators, "protocol": "direct_scaled"}
        tuning_trials = pd.DataFrame()
    elif model_name == "lightgbm_tuned_direct":
        checkpoint_path = (
            Path(args.out_dir)
            / run_id
            / f"tuning_trials_{dataset.lower()}_h{horizon}_{model_name}.csv"
        )
        tuned_params, tuning_trials = tune_lightgbm_params(
            "direct",
            y_wide,
            cov_wide,
            covariate_cols,
            dates,
            starts,
            horizon,
            args.train_window_days,
            args.lightgbm_tuning_trials,
            args.seed + 1000 + horizon,
            checkpoint_path=checkpoint_path,
        )
        y_true, y_pred, eval_t, origin_t = evaluate_lightgbm_direct(
            y_wide,
            cov_wide,
            covariate_cols,
            dates,
            starts,
            horizon,
            args.train_window_days,
            params=tuned_params,
        )
        model_params = {
            "protocol": "direct_tuned",
            "tuning_trials": args.lightgbm_tuning_trials,
            "selected_params": tuned_params,
        }
    elif model_name in FM_MODELS:
        tuning_trials = pd.DataFrame()
        if model_name == "timesfm25":
            from models.foundation.timesfm25 import TimesFM25Forecaster

            y_true, y_pred, eval_t, origin_t = evaluate_fm_batch(
                y_wide, starts, horizon, TimesFM25Forecaster(device="cpu")
            )
            model_params = {"protocol": "zero_shot_univariate_batched"}
        elif model_name == "tirex":
            from models.foundation.tirex import TiRexForecaster

            device = tirex_device_for(args.hardware)
            y_true, y_pred, eval_t, origin_t = evaluate_fm_batch(
                y_wide, starts, horizon, TiRexForecaster(device=device)
            )
            model_params = {"protocol": "zero_shot_univariate_batched", "device": device}
        else:
            predictor = get_fm_predictor(model_name, args.hardware)
            y_true, y_pred, eval_t, origin_t = evaluate_fm(y_wide, starts, horizon, predictor)
            model_params = {"protocol": "zero_shot_univariate"}
    else:
        raise ValueError(f"Unknown model: {model_name}")
    tracker.stop()
    elapsed = time.time() - start_time
    predictions = predictions_from_wide(
        series_ids, dates, y_true, y_pred, eval_t, origin_t,
        model_name, dataset, horizon, run_id, panel_id,
    )
    cost = tracker.to_dict(n_series=len(series_ids))
    meta = {
        "run_id": run_id,
        "panel_id": panel_id,
        "dataset": dataset,
        "horizon": horizon,
        "model_name": model_name,
        "hardware": args.hardware,
        "runtime_sec": cost["runtime_sec"],
        "wall_clock_sec": elapsed,
        "cost_usd": cost["cost_usd"],
        "co2_kg": cost["co2_kg"],
        "series_per_second": cost["series_per_second"],
        "n_eval_origins": len(starts),
        "train_fraction": args.train_fraction,
        "train_window_days": args.train_window_days,
        "series_selection": args.series_selection,
        "model_params_json": json.dumps(model_params, sort_keys=True),
    }
    if not tuning_trials.empty:
        tuning_trials = tuning_trials.copy()
        tuning_trials.insert(0, "run_id", run_id)
        tuning_trials.insert(1, "panel_id", panel_id)
        tuning_trials.insert(2, "dataset", dataset)
        tuning_trials.insert(3, "horizon", horizon)
        tuning_trials.insert(4, "model_name", model_name)
    return predictions, meta, tuning_trials


def portable_path(path_value: str) -> str:
    path = Path(path_value)
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Matched-panel Source B rerun")
    parser.add_argument("--datasets", nargs="+", default=["m5", "rohlik", "favorita"])
    parser.add_argument("--models", nargs="+", default=["seasonal_naive", "lightgbm_cov", "lightgbm_direct"])
    parser.add_argument("--horizons", nargs="+", type=int, default=[7, 14, 28])
    parser.add_argument("--max-series", type=int, default=100)
    parser.add_argument(
        "--series-selection",
        choices=["top_volume", "random", "stratified_volume_zero"],
        default="top_volume",
    )
    parser.add_argument("--seed", type=int, default=20260714)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    parser.add_argument("--train-window-days", type=int, default=365)
    parser.add_argument("--lightgbm-tuning-trials", type=int, default=20)
    parser.add_argument("--hardware", default="M_SERIES_MAC")
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "benchmark/results/source_b_paired_panel"))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    run_id = args.run_id or time.strftime("source_b_paired_%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Writing Source B paired-panel rerun to {out_dir}")

    all_predictions = []
    run_meta = []
    tuning_trial_frames = []
    panel_rows = []
    for dataset_arg in args.datasets:
        bundle = load_dataset(dataset_arg)
        selected = select_series_ids(bundle.frame, args.max_series, args.series_selection, args.seed)
        dense = densify_panel(bundle.frame, selected, bundle.covariate_cols)
        series_ids, dates, y_wide, cov_wide = make_wide(dense, bundle.covariate_cols)
        panel_id = f"{bundle.name.lower()}_{args.series_selection}_{len(series_ids)}_{args.seed}"
        pd.DataFrame({"panel_id": panel_id, "dataset": bundle.name, "series_id": series_ids}).to_csv(
            out_dir / f"panel_series_{bundle.name.lower()}.csv", index=False
        )
        panel_rows.append(
            {
                "run_id": run_id,
                "panel_id": panel_id,
                "dataset": bundle.name,
                "n_series": len(series_ids),
                "n_dates": len(dates),
                "first_date": str(pd.Timestamp(dates[0]).date()),
                "last_date": str(pd.Timestamp(dates[-1]).date()),
                "series_selection": args.series_selection,
                "seed": args.seed,
            }
        )
        for horizon in args.horizons:
            starts = eval_starts_for(len(dates), horizon, args.train_fraction)
            for model_name in args.models:
                predictions, meta, tuning_trials = run_cell(
                    model_name, bundle.name, horizon, series_ids, dates, y_wide,
                    cov_wide, bundle.covariate_cols, starts, args, run_id, panel_id
                )
                all_predictions.append(predictions)
                run_meta.append(meta)
                if not tuning_trials.empty:
                    tuning_trial_frames.append(tuning_trials)
                cell_slug = f"{bundle.name.lower()}_h{horizon}_{model_name}"
                predictions.to_parquet(out_dir / f"predictions_{cell_slug}.parquet", index=False)
                pd.DataFrame(run_meta).to_csv(out_dir / "run_ledger_incremental.csv", index=False)
                if tuning_trial_frames:
                    pd.concat(tuning_trial_frames, ignore_index=True).to_csv(
                        out_dir / "lightgbm_tuning_trials_incremental.csv",
                        index=False,
                    )

    predictions_df = pd.concat(all_predictions, ignore_index=True) if all_predictions else pd.DataFrame()
    metrics_df = per_series_metrics(predictions_df)
    summary_df = cell_summary(metrics_df, run_meta)
    contrasts_df = paired_bootstrap(metrics_df, summary_df, args.n_bootstrap, args.seed)
    tuning_trials_df = (
        pd.concat(tuning_trial_frames, ignore_index=True)
        if tuning_trial_frames
        else pd.DataFrame()
    )

    pd.DataFrame(panel_rows).to_csv(out_dir / "panel_manifest.csv", index=False)
    pd.DataFrame(run_meta).to_csv(out_dir / "run_ledger.csv", index=False)
    predictions_df.to_parquet(out_dir / "predictions_all.parquet", index=False)
    metrics_df.to_csv(out_dir / "per_series_metrics.csv", index=False)
    summary_df.to_csv(out_dir / "cell_summary.csv", index=False)
    contrasts_df.to_csv(out_dir / "paired_bootstrap_contrasts.csv", index=False)
    if not tuning_trials_df.empty:
        tuning_trials_df.to_csv(out_dir / "lightgbm_tuning_trials.csv", index=False)
    with (out_dir / "run_config.json").open("w", encoding="utf-8") as fh:
        config = vars(args) | {"out_dir": portable_path(args.out_dir), "run_id": run_id}
        json.dump(config, fh, indent=2, sort_keys=True)
    print("Done.")
    print(summary_df[["dataset", "horizon", "model_name", "n_series", "WAPE_aggregate", "WAPE_mean", "runtime_sec"]])
    if not contrasts_df.empty:
        print(contrasts_df[["dataset", "horizon", "model_name", "baseline_model", "log_ratio", "bootstrap_se", "ci95_low", "ci95_high"]])


if __name__ == "__main__":
    main()
