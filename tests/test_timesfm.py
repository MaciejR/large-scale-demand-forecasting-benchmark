"""Tests for TimesFM 2.5 foundation model wrapper."""

import sys
sys.path.insert(0, "benchmark/code")

import numpy as np
import pandas as pd
import pytest

from models.foundation.timesfm25 import TimesFM25Forecaster


def _timesfm_available():
    try:
        import timesfm
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _timesfm_available(), reason="timesfm not installed")
def test_predict_returns_correct_length():
    np.random.seed(42)
    train = pd.Series(np.random.randn(100).cumsum() + 50)
    model = TimesFM25Forecaster()
    pred = model.predict(train, horizon=7)
    assert len(pred) == 7
    assert isinstance(pred, pd.Series)


@pytest.mark.skipif(not _timesfm_available(), reason="timesfm not installed")
def test_predict_values_are_finite():
    np.random.seed(42)
    train = pd.Series(np.random.randn(200).cumsum() + 100)
    model = TimesFM25Forecaster()
    pred = model.predict(train, horizon=14)
    assert np.all(np.isfinite(pred.values))


def test_interface_exists():
    model = TimesFM25Forecaster.__new__(TimesFM25Forecaster)
    assert hasattr(model, "predict")
