#!/usr/bin/env python3
"""Run fev-bench tasks with the official fev evaluation windows.

This runner is intentionally separate from run_gap_filling.py.  It uses
fev.Task.iter_windows(), writes prediction-level artifacts, and can therefore
feed paired bootstrap/covariance analyses instead of relying on leaderboard
summary rows alone.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Callable

import fev
import numpy as np
import pandas as pd
from datasets import Dataset

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.loaders.fev_bench import RETAIL_TASKS, _TASK_DEFS  # noqa: E402


QUANTILE_LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
PREDICTION_ARTIFACT_SCHEMA = "v2_quantile_head"


def _make_task(task_name: str) -> fev.Task:
    task_def = _TASK_DEFS[task_name]
    return fev.Task(
        dataset_path="autogluon/fev_datasets",
        dataset_config=task_name,
        horizon=task_def["horizon"],
        num_windows=task_def["num_windows"],
        seasonality=task_def["seasonality"],
        eval_metric="SQL",
        extra_metrics=["MASE", "WAPE"],
        quantile_levels=QUANTILE_LEVELS,
        target=task_def.get("target", "target"),
        known_dynamic_columns=task_def.get("known_dynamic_columns", []),
        past_dynamic_columns=task_def.get("past_dynamic_columns", []),
        static_columns=task_def.get("static_columns", []),
    )


def _clean_history(values: np.ndarray, fill_missing: str) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    if fill_missing == "zero":
        return np.nan_to_num(arr, nan=0.0)
    if fill_missing == "ffill_zero":
        series = pd.Series(arr).ffill().fillna(0.0)
        return series.to_numpy(dtype=np.float32)
    if np.isnan(arr).any():
        raise ValueError("History contains NaN; choose --fill-missing zero or ffill_zero.")
    return arr


def _point_row(point: np.ndarray) -> dict[str, list[float]]:
    pred = np.asarray(point, dtype=np.float32).reshape(-1).tolist()
    row = {"predictions": pred}
    for q in QUANTILE_LEVELS:
        row[str(q)] = pred
    return row


def _seasonal_naive_predictor(
    train: pd.Series,
    horizon: int,
    seasonality: int,
) -> dict[str, list[float]]:
    history = train.to_numpy(dtype=np.float32)
    if len(history) == 0:
        point = np.zeros(horizon, dtype=np.float32)
    else:
        last_season = history[-min(seasonality, len(history)):]
        repeats = int(math.ceil(horizon / len(last_season)))
        point = np.tile(last_season, repeats)[:horizon].astype(np.float32)
    return _point_row(point)


def _load_point_forecaster(model_name: str, hardware: str) -> Callable:
    from experiments.run_gap_filling import _device_for_hardware, get_model_fn

    device = _device_for_hardware(hardware)
    if model_name == "chronos2":
        from models.foundation.chronos2 import Chronos2Forecaster

        forecaster = Chronos2Forecaster(device=device)

        def predict(train: pd.Series, horizon: int, seasonality: int) -> dict[str, list[float]]:
            qdf = forecaster.predict_quantiles(train, horizon, levels=QUANTILE_LEVELS)
            row = {"predictions": qdf["mean"].to_numpy(dtype=np.float32).tolist()}
            for q in QUANTILE_LEVELS:
                row[str(q)] = qdf[f"q{q}"].to_numpy(dtype=np.float32).tolist()
            return row

        return predict

    forecast_fn, _ = get_model_fn(model_name, hardware)

    def predict(train: pd.Series, horizon: int, seasonality: int) -> dict[str, list[float]]:
        return _point_row(forecast_fn(train, horizon).to_numpy(dtype=np.float32))

    return predict


def _load_batch_forecaster(model_name: str, hardware: str):
    from experiments.run_gap_filling import _device_for_hardware

    device = _device_for_hardware(hardware)
    if model_name == "chronos_bolt_tiny":
        from models.foundation.chronos_bolt_tiny import ChronosBoltTinyForecaster

        forecaster = ChronosBoltTinyForecaster(device=device)
        return forecaster.predict_batch
    if model_name == "chronos2":
        from models.foundation.chronos2 import Chronos2Forecaster

        forecaster = Chronos2Forecaster(device=device)
        return forecaster.predict_batch
    if model_name == "tirex":
        from models.foundation.tirex import TiRexForecaster

        forecaster = TiRexForecaster(device=device)
        return forecaster.predict_batch
    if model_name == "timesfm25":
        from models.foundation.timesfm25 import TimesFM25Forecaster

        forecaster = TimesFM25Forecaster(device=device)
        return forecaster.predict_batch
    return None


def _normalise_batch_output(batch_output, horizon: int) -> tuple[np.ndarray, dict[float, np.ndarray]]:
    if isinstance(batch_output, tuple):
        mean_arr, quantile_map = batch_output
    else:
        mean_arr = batch_output
        quantile_map = {}

    mean_arr = np.asarray(mean_arr, dtype=np.float32)
    if mean_arr.ndim == 1:
        mean_arr = mean_arr.reshape(1, -1)
    mean_arr = mean_arr[:, :horizon]

    normalised_quantiles = {}
    for q in QUANTILE_LEVELS:
        if q in quantile_map:
            q_arr = np.asarray(quantile_map[q], dtype=np.float32)
        elif str(q) in quantile_map:
            q_arr = np.asarray(quantile_map[str(q)], dtype=np.float32)
        else:
            q_arr = mean_arr
        if q_arr.ndim == 1:
            q_arr = q_arr.reshape(1, -1)
        normalised_quantiles[q] = q_arr[:, :horizon]

    return mean_arr, normalised_quantiles


def _series_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not mask.any():
        return float("nan")
    denom = float(np.abs(y_true[mask]).sum())
    if denom == 0:
        return float("nan")
    return float(np.abs(y_true[mask] - y_pred[mask]).sum() / denom)


def _series_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not mask.any():
        return float("nan")
    return float(np.abs(y_true[mask] - y_pred[mask]).mean())


def _flatten_window_predictions(
    *,
    task_name: str,
    model_name: str,
    target: str,
    window_idx: int,
    predictions: list[dict[str, list[float]]],
    ground_truth: Dataset,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    metric_rows = []
    for pred_row, truth_row in zip(predictions, ground_truth, strict=True):
        series_id = truth_row["id"]
        timestamps = truth_row["timestamp"]
        y_true = np.asarray(truth_row[target], dtype=np.float32)
        y_pred = np.asarray(pred_row["predictions"], dtype=np.float32)
        metric_rows.append(
            {
                "task_name": task_name,
                "model_name": model_name,
                "window_idx": window_idx,
                "series_id": series_id,
                "WAPE": _series_wape(y_true, y_pred),
                "MAE": _series_mae(y_true, y_pred),
                "n_obs": int(np.isfinite(y_true).sum()),
            }
        )
        for step, (ts, actual, point) in enumerate(zip(timestamps, y_true, y_pred, strict=True)):
            row = {
                "task_name": task_name,
                "model_name": model_name,
                "window_idx": window_idx,
                "series_id": series_id,
                "step": step + 1,
                "timestamp": str(ts),
                "y_true": float(actual) if np.isfinite(actual) else np.nan,
                "prediction": float(point) if np.isfinite(point) else np.nan,
            }
            for q in QUANTILE_LEVELS:
                values = np.asarray(pred_row[str(q)], dtype=np.float32)
                row[f"q{q}"] = float(values[step]) if np.isfinite(values[step]) else np.nan
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(metric_rows)


def _window_artifact_paths(output_dir: Path, window_idx: int) -> dict[str, Path]:
    window_dir = output_dir / f"windows_{PREDICTION_ARTIFACT_SCHEMA}"
    stem = f"window_{window_idx:03d}"
    return {
        "predictions": window_dir / f"{stem}_predictions.json",
        "long": window_dir / f"{stem}_predictions_long.parquet",
        "metrics": window_dir / f"{stem}_per_series_metrics.csv",
    }


def _batch_artifact_path(
    output_dir: Path,
    window_idx: int,
    batch_start: int,
    batch_size: int,
) -> Path:
    batch_dir = (
        output_dir
        / f"windows_{PREDICTION_ARTIFACT_SCHEMA}"
        / f"window_{window_idx:03d}_batches_bs{batch_size:04d}"
    )
    return batch_dir / f"batch_{batch_start:06d}.json"


def run_task(
    *,
    task_name: str,
    model_name: str,
    output_dir: Path,
    hardware: str,
    fill_missing: str,
    batch_size: int,
    batch_shard_index: int = 0,
    batch_shard_count: int = 1,
) -> None:
    if batch_shard_count < 1:
        raise ValueError("batch_shard_count must be at least 1")
    if not 0 <= batch_shard_index < batch_shard_count:
        raise ValueError(
            "batch_shard_index must be between 0 and batch_shard_count - 1"
        )

    task = _make_task(task_name)
    target = task.target if isinstance(task.target, str) else task.target[0]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"windows_{PREDICTION_ARTIFACT_SCHEMA}").mkdir(
        parents=True,
        exist_ok=True,
    )

    batch_predictor = _load_batch_forecaster(model_name, hardware)
    if model_name == "seasonal_naive":
        predictor = _seasonal_naive_predictor
    else:
        predictor = _load_point_forecaster(model_name, hardware)

    predictions_per_window = []
    long_frames = []
    metric_frames = []
    start = time.time()
    for window_idx, window in enumerate(task.iter_windows()):
        window_paths = _window_artifact_paths(output_dir, window_idx)
        if all(path.exists() for path in window_paths.values()):
            with window_paths["predictions"].open() as f:
                predictions = json.load(f)
            predictions_per_window.append(Dataset.from_list(predictions))
            long_frames.append(pd.read_parquet(window_paths["long"]))
            metric_frames.append(pd.read_csv(window_paths["metrics"]))
            print(
                f"{task_name}/{model_name}: window {window_idx + 1}/{task.num_windows}, "
                f"{len(predictions)} series (checkpoint)",
                flush=True,
            )
            continue

        past_df, future_df, _ = fev.convert_input_data(window, adapter="pandas")
        history_by_id = {
            series_id: group[target].to_numpy(dtype=np.float32)
            for series_id, group in past_df.groupby("id", sort=False)
        }
        predictions = []
        series_ids = list(future_df["id"].drop_duplicates())
        if batch_predictor is not None:
            for batch_start in range(0, len(series_ids), batch_size):
                batch_index = batch_start // batch_size
                if batch_index % batch_shard_count != batch_shard_index:
                    continue
                batch_ids = series_ids[batch_start : batch_start + batch_size]
                batch_path = _batch_artifact_path(
                    output_dir,
                    window_idx,
                    batch_start,
                    batch_size,
                )
                if batch_path.exists():
                    with batch_path.open() as f:
                        batch_payload = json.load(f)
                    if batch_payload.get("series_ids") != batch_ids:
                        raise ValueError(
                            f"Batch checkpoint series mismatch for {batch_path}"
                        )
                    predictions.extend(batch_payload["predictions"])
                    print(
                        f"{task_name}/{model_name}: window {window_idx + 1}/{task.num_windows}, "
                        f"batch {batch_start // batch_size + 1} checkpoint",
                        flush=True,
                    )
                    continue

                histories = [
                    _clean_history(history_by_id[series_id], fill_missing)
                    for series_id in batch_ids
                ]
                batch_output = batch_predictor(
                    histories,
                    task.horizon,
                    quantile_levels=QUANTILE_LEVELS,
                )
                mean_arr, quantile_map = _normalise_batch_output(batch_output, task.horizon)
                for row_idx in range(len(batch_ids)):
                    row = {
                        "predictions": mean_arr[row_idx].astype(np.float32).tolist()
                    }
                    for q in QUANTILE_LEVELS:
                        row[str(q)] = quantile_map[q][row_idx].astype(np.float32).tolist()
                    predictions.append(row)
                batch_predictions = predictions[-len(batch_ids):]
                batch_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = batch_path.with_suffix(".json.tmp")
                with tmp_path.open("w") as f:
                    json.dump(
                        {
                            "task_name": task_name,
                            "model_name": model_name,
                            "window_idx": window_idx,
                            "batch_start": batch_start,
                            "series_ids": batch_ids,
                            "predictions": batch_predictions,
                        },
                        f,
                    )
                tmp_path.replace(batch_path)
                print(
                    f"{task_name}/{model_name}: window {window_idx + 1}/{task.num_windows}, "
                    f"batch {batch_index + 1}, {len(batch_ids)} series",
                    flush=True,
                )
            if batch_shard_count > 1:
                print(
                    f"{task_name}/{model_name}: checkpoint shard "
                    f"{batch_shard_index + 1}/{batch_shard_count} complete for "
                    f"window {window_idx + 1}/{task.num_windows}",
                    flush=True,
                )
                continue
        else:
            if batch_shard_count > 1:
                raise ValueError("Batch sharding requires a batch-capable model")
            for series_id in series_ids:
                history = history_by_id[series_id]
                history = _clean_history(history, fill_missing)
                predictions.append(
                    predictor(
                        pd.Series(history),
                        task.horizon,
                        task.seasonality,
                    )
                )
        predictions_per_window.append(Dataset.from_list(predictions))
        long_df, metrics_df = _flatten_window_predictions(
            task_name=task_name,
            model_name=model_name,
            target=target,
            window_idx=window_idx,
            predictions=predictions,
            ground_truth=window.get_ground_truth(),
        )
        long_frames.append(long_df)
        metric_frames.append(metrics_df)
        with window_paths["predictions"].open("w") as f:
            json.dump(predictions, f)
        long_df.to_parquet(window_paths["long"], index=False)
        metrics_df.to_csv(window_paths["metrics"], index=False)
        print(
            f"{task_name}/{model_name}: window {window_idx + 1}/{task.num_windows}, "
            f"{len(predictions)} series",
            flush=True,
        )

    if batch_shard_count > 1:
        print(
            f"Done checkpoint shard {batch_shard_index + 1}/{batch_shard_count} "
            f"for {task_name}/{model_name}",
            flush=True,
        )
        return

    elapsed = time.time() - start
    summary = task.evaluation_summary(
        predictions_per_window,
        model_name=model_name,
        inference_time_s=elapsed,
        trained_on_this_dataset=False,
        extra_info={
            "fill_missing": fill_missing,
            "runner": "run_fev_bench_official.py",
            "prediction_artifact_schema": PREDICTION_ARTIFACT_SCHEMA,
            "quantile_source": (
                "timesfm_continuous_quantile_head"
                if model_name == "timesfm25"
                else "model_or_point_fallback"
            ),
        },
    )

    predictions_long = pd.concat(long_frames, ignore_index=True)
    per_series_metrics = pd.concat(metric_frames, ignore_index=True)
    predictions_long.to_parquet(output_dir / "predictions_long.parquet", index=False)
    per_series_metrics.to_csv(output_dir / "per_series_window_metrics.csv", index=False)
    with (output_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    with (output_dir / "run_config.json").open("w") as f:
        json.dump(
            {
                "task_name": task_name,
                "model_name": model_name,
                "hardware": hardware,
                "fill_missing": fill_missing,
                "quantile_levels": QUANTILE_LEVELS,
                "batch_size": batch_size,
                "elapsed_seconds": elapsed,
                "prediction_artifact_schema": PREDICTION_ARTIFACT_SCHEMA,
                "quantile_source": (
                    "timesfm_continuous_quantile_head"
                    if model_name == "timesfm25"
                    else "model_or_point_fallback"
                ),
            },
            f,
            indent=2,
        )

    print(
        f"Done {task_name}/{model_name}: SQL={summary.get('test_error'):.6f}, "
        f"MASE={summary.get('MASE'):.6f}, WAPE={summary.get('WAPE'):.6f}, "
        f"forecasts={summary.get('num_forecasts')}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run official fev-bench windows.")
    parser.add_argument("--task", required=True, choices=RETAIL_TASKS)
    parser.add_argument(
        "--model",
        required=True,
        choices=[
            "seasonal_naive",
            "chronos2",
            "chronos_bolt_tiny",
            "timesfm25",
            "moirai2",
            "tabpfn_ts",
            "tirex",
        ],
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--hardware", default="M_SERIES_MAC")
    parser.add_argument(
        "--fill-missing",
        default="zero",
        choices=["zero", "ffill_zero", "error"],
        help="How to handle missing historical target values before model inference.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("benchmark/results/fev_bench_official"),
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--batch-shard-index", type=int, default=0)
    parser.add_argument("--batch-shard-count", type=int, default=1)
    args = parser.parse_args()

    run_id = args.run_id or time.strftime("fev_official_%Y%m%d_%H%M%S")
    output_dir = args.output_root / run_id / args.task / args.model
    run_task(
        task_name=args.task,
        model_name=args.model,
        output_dir=output_dir,
        hardware=args.hardware,
        fill_missing=args.fill_missing,
        batch_size=args.batch_size,
        batch_shard_index=args.batch_shard_index,
        batch_shard_count=args.batch_shard_count,
    )


if __name__ == "__main__":
    main()
