"""Tests for Chronos-2 foundation model wrapper."""

import sys
sys.path.insert(0, "benchmark/code")

import numpy as np
import pandas as pd
import pytest

from models.foundation.chronos2 import Chronos2Forecaster


def _chronos_available():
    try:
        from chronos import BaseChronosPipeline
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _chronos_available(), reason="chronos-forecasting not installed")
def test_predict_returns_correct_length():
    np.random.seed(42)
    train = pd.Series(np.random.randn(100).cumsum() + 50)
    model = Chronos2Forecaster(device="cpu")
    pred = model.predict(train, horizon=7)
    assert len(pred) == 7
    assert isinstance(pred, pd.Series)


@pytest.mark.skipif(not _chronos_available(), reason="chronos-forecasting not installed")
def test_predict_values_are_finite():
    np.random.seed(42)
    train = pd.Series(np.random.randn(200).cumsum() + 100)
    model = Chronos2Forecaster(device="cpu")
    pred = model.predict(train, horizon=14)
    assert np.all(np.isfinite(pred.values))


def test_interface_exists():
    """Verify the class can be instantiated without the model loaded."""
    model = Chronos2Forecaster.__new__(Chronos2Forecaster)
    assert hasattr(model, "predict")
