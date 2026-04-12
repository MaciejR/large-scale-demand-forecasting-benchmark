"""Tests for covariate-aware LightGBM forecaster."""

import sys
sys.path.insert(0, "benchmark/code")

import numpy as np
import pandas as pd
import pytest

from models.ml.lightgbm_covariates import LightGBMCovariateForecaster


@pytest.fixture
def train_df():
    np.random.seed(42)
    n = 100
    records = []
    for sid in ["A", "B"]:
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        price = np.random.uniform(5, 15, n)
        promo = np.random.binomial(1, 0.2, n)
        base = np.tile([10, 12, 15, 14, 20, 25, 8], 15)[:n]
        y = base - 0.5 * price + 3 * promo + np.random.normal(0, 1, n)
        records.append(pd.DataFrame({
            "series_id": sid,
            "ds": dates,
            "y": y,
            "price": price,
            "promo": promo.astype(float),
        }))
    return pd.concat(records, ignore_index=True)


def test_fit_does_not_error(train_df):
    model = LightGBMCovariateForecaster(covariate_columns=["price", "promo"])
    model.fit(train_df)
    assert model.model_ is not None


def test_predict_returns_correct_length(train_df):
    model = LightGBMCovariateForecaster(covariate_columns=["price", "promo"])
    model.fit(train_df)
    future = pd.DataFrame({
        "price": [10.0] * 7,
        "promo": [0.0] * 7,
    })
    history = train_df[train_df["series_id"] == "A"]
    pred = model.predict(history, horizon=7, future_covariates=future)
    assert len(pred) == 7
    assert isinstance(pred, pd.Series)


def test_predict_uses_covariates(train_df):
    """Promo=1 should produce higher forecasts than promo=0."""
    model = LightGBMCovariateForecaster(covariate_columns=["price", "promo"])
    model.fit(train_df)
    history = train_df[train_df["series_id"] == "A"]

    future_no_promo = pd.DataFrame({"price": [10.0] * 7, "promo": [0.0] * 7})
    future_promo = pd.DataFrame({"price": [10.0] * 7, "promo": [1.0] * 7})

    pred_no = model.predict(history, horizon=7, future_covariates=future_no_promo)
    pred_yes = model.predict(history, horizon=7, future_covariates=future_promo)
    assert pred_yes.mean() > pred_no.mean()
