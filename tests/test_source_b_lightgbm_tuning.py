"""Tests for Source B tuned LightGBM support."""

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "analysis")
sys.path.insert(0, "benchmark/code/experiments")

from source_b_paired_panel_report import build_contrast_definitions
from run_source_b_paired_panel import (
    BASELINE_MODELS,
    _lightgbm_params,
    evaluate_lightgbm_recursive,
    eval_starts_for,
    make_wide,
    select_series_ids,
    tune_lightgbm_params,
)


def _small_panel() -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray], tuple[str, ...]]:
    rng = np.random.default_rng(123)
    rows = []
    dates = pd.date_range("2025-01-01", periods=80, freq="D")
    for sid, offset in [("A", 0.0), ("B", 3.0), ("C", 6.0)]:
        promo = rng.binomial(1, 0.25, size=len(dates)).astype(float)
        y = 20 + offset + 4 * promo + np.sin(np.arange(len(dates)) / 4)
        for ds, yi, pi in zip(dates, y, promo):
            rows.append({"series_id": sid, "ds": ds, "y": yi, "promo": pi})
    dense = pd.DataFrame(rows)
    _, wide_dates, y_wide, cov_wide = make_wide(dense, ("promo",))
    return wide_dates, y_wide, cov_wide, ("promo",)


def test_tuned_lightgbm_models_are_baselines():
    assert "lightgbm_tuned_cov" in BASELINE_MODELS
    assert "lightgbm_tuned_direct" in BASELINE_MODELS

    summary = pd.DataFrame(
        [
            {"dataset": "D", "horizon": 7, "model_name": "lightgbm_tuned_cov", "WAPE_aggregate": 0.10},
            {"dataset": "D", "horizon": 7, "model_name": "lightgbm_cov", "WAPE_aggregate": 0.20},
            {"dataset": "D", "horizon": 7, "model_name": "fm_a", "WAPE_aggregate": 0.15},
        ]
    )
    contrasts = build_contrast_definitions(summary)
    assert contrasts.iloc[0]["baseline_model"] == "lightgbm_tuned_cov"


def test_tune_lightgbm_params_records_trials_and_returns_selected_params():
    dates, y_wide, cov_wide, covariate_cols = _small_panel()
    starts = eval_starts_for(len(dates), horizon=7, train_fraction=0.75)

    params, trials = tune_lightgbm_params(
        "recursive",
        y_wide,
        cov_wide,
        covariate_cols,
        dates,
        starts,
        horizon=7,
        train_window_days=40,
        n_trials=3,
        seed=99,
    )

    assert len(trials) == 3
    assert set(["trial", "validation_WAPE_aggregate", "params_json"]).issubset(trials.columns)
    assert params["objective"] == "tweedie"
    assert params == _lightgbm_params(seed=99) or "num_leaves" in params

    y_true, y_pred, _, _ = evaluate_lightgbm_recursive(
        y_wide,
        cov_wide,
        covariate_cols,
        dates,
        starts,
        horizon=7,
        train_window_days=40,
        params=params,
    )
    assert y_true.shape == y_pred.shape
    assert np.isfinite(y_pred).all()


def test_tune_lightgbm_params_resumes_from_checkpoint(tmp_path):
    dates, y_wide, cov_wide, covariate_cols = _small_panel()
    starts = eval_starts_for(len(dates), horizon=7, train_fraction=0.75)
    checkpoint_path = tmp_path / "tuning_trials.csv"

    first_params, first_trials = tune_lightgbm_params(
        "recursive",
        y_wide,
        cov_wide,
        covariate_cols,
        dates,
        starts,
        horizon=7,
        train_window_days=40,
        n_trials=2,
        seed=99,
        checkpoint_path=checkpoint_path,
    )

    assert checkpoint_path.exists()
    assert len(first_trials) == 2

    resumed_params, resumed_trials = tune_lightgbm_params(
        "recursive",
        y_wide,
        cov_wide,
        covariate_cols,
        dates,
        starts,
        horizon=7,
        train_window_days=40,
        n_trials=4,
        seed=99,
        checkpoint_path=checkpoint_path,
    )

    checkpoint = pd.read_csv(checkpoint_path)
    assert len(resumed_trials) == 4
    assert len(checkpoint) == 4
    assert checkpoint["trial"].tolist() == [0, 1, 2, 3]
    pd.testing.assert_frame_equal(
        first_trials.reset_index(drop=True),
        resumed_trials.iloc[:2].reset_index(drop=True),
        check_dtype=False,
    )
    assert first_params["objective"] == "tweedie"
    assert resumed_params["objective"] == "tweedie"


def test_stratified_volume_zero_selection_includes_intermittent_tail():
    rows = []
    dates = pd.date_range("2025-01-01", periods=20, freq="D")
    for idx in range(40):
        sid = f"S{idx:02d}"
        if idx < 10:
            y = np.full(len(dates), 100 + idx, dtype=float)
        elif idx < 20:
            y = np.where(np.arange(len(dates)) % 2 == 0, 10 + idx, 0.0)
        elif idx < 30:
            y = np.full(len(dates), 5 + idx / 10, dtype=float)
        else:
            y = np.where(np.arange(len(dates)) % 5 == 0, 2.0, 0.0)
        for ds, yi in zip(dates, y):
            rows.append({"series_id": sid, "ds": ds, "y": yi})
    frame = pd.DataFrame(rows)

    selected = select_series_ids(frame, max_series=12, method="stratified_volume_zero", seed=7)
    selected_stats = frame[frame["series_id"].isin(selected)].groupby("series_id")["y"].agg(
        total_volume="sum",
        zero_fraction=lambda s: float((s <= 0).mean()),
    )

    assert len(selected) == 12
    assert selected_stats["zero_fraction"].max() >= 0.75
    assert selected_stats["total_volume"].min() < selected_stats["total_volume"].max()
