"""Shared test fixtures for benchmark tests."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def daily_series():
    """A simple daily series: 4 weeks of data with weekly pattern."""
    np.random.seed(42)
    n = 28
    pattern = [10, 12, 15, 14, 20, 25, 8]  # Mon-Sun
    values = np.tile(pattern, 4) + np.random.normal(0, 1, n)
    return pd.Series(values, name="y")


@pytest.fixture
def multi_series_df():
    """DataFrame with 3 series, 56 days each, columns [series_id, ds, y]."""
    np.random.seed(42)
    records = []
    pattern = [10, 12, 15, 14, 20, 25, 8]
    for sid in ["A", "B", "C"]:
        dates = pd.date_range("2023-01-01", periods=56, freq="D")
        values = np.tile(pattern, 8) + np.random.normal(0, 2, 56)
        records.append(pd.DataFrame({
            "series_id": sid,
            "ds": dates,
            "y": values,
        }))
    return pd.concat(records, ignore_index=True)


@pytest.fixture
def multi_series_with_covariates():
    """DataFrame with [series_id, ds, y, price, promo] for covariate tests."""
    np.random.seed(42)
    records = []
    for sid in ["A", "B", "C"]:
        n = 56
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        base = np.tile([10, 12, 15, 14, 20, 25, 8], 8)
        price = np.random.uniform(5, 15, n)
        promo = np.random.binomial(1, 0.2, n)
        values = base - 0.5 * price + 3 * promo + np.random.normal(0, 1, n)
        records.append(pd.DataFrame({
            "series_id": sid,
            "ds": dates,
            "y": values,
            "price": price,
            "promo": promo.astype(float),
        }))
    return pd.concat(records, ignore_index=True)
