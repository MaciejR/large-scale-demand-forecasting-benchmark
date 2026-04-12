"""Tests for Seasonal Naive forecaster."""

import numpy as np
import pandas as pd
import pytest

import sys
sys.path.insert(0, "benchmark/code")

from models.baselines.seasonal_naive import seasonal_naive_forecast


def test_repeats_last_week():
    """Forecast should repeat the last full seasonal cycle."""
    pattern = [10, 12, 15, 14, 20, 25, 8]
    train = pd.Series(pattern * 4)  # 4 full weeks
    result = seasonal_naive_forecast(train, horizon=7)
    assert list(result) == pattern


def test_horizon_longer_than_season():
    """14-day forecast should tile the last week twice."""
    pattern = [1, 2, 3, 4, 5, 6, 7]
    train = pd.Series(pattern * 3)
    result = seasonal_naive_forecast(train, horizon=14)
    assert list(result) == pattern * 2


def test_partial_horizon():
    """5-day forecast should be first 5 days of last week."""
    pattern = [10, 20, 30, 40, 50, 60, 70]
    train = pd.Series(pattern * 2)
    result = seasonal_naive_forecast(train, horizon=5)
    assert list(result) == [10, 20, 30, 40, 50]


def test_custom_season_length():
    """Support non-7 seasonal periods."""
    pattern = [1, 2, 3]
    train = pd.Series(pattern * 5)
    result = seasonal_naive_forecast(train, horizon=7, season_length=3)
    assert list(result) == [1, 2, 3, 1, 2, 3, 1]


def test_returns_series():
    """Output type must be pd.Series."""
    train = pd.Series([1, 2, 3, 4, 5, 6, 7] * 2)
    result = seasonal_naive_forecast(train, horizon=7)
    assert isinstance(result, pd.Series)
    assert len(result) == 7
