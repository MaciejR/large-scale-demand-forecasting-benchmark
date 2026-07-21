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
