"""Tests for TiRex foundation model wrapper."""

import sys

sys.path.insert(0, "benchmark/code")

import numpy as np
import pytest

from models.foundation.tirex import TiRexForecaster


def test_interface_exists():
    model = TiRexForecaster.__new__(TiRexForecaster)
    assert hasattr(model, "predict")
    assert hasattr(model, "predict_batch")


def test_predict_batch_with_loaded_fake_model():
    torch = pytest.importorskip("torch")

    class FakeModel:
        def forecast(self, context, prediction_length):
            batch = context.shape[0]
            mean = torch.ones((batch, prediction_length), dtype=torch.float32)
            return None, mean

    model = TiRexForecaster.__new__(TiRexForecaster)
    model._model = FakeModel()
    histories = [np.arange(10, dtype=np.float32), np.arange(10, dtype=np.float32) + 1]

    pred = model.predict_batch(histories, horizon=4)

    assert pred.shape == (2, 4)
    assert np.all(np.isfinite(pred))


def test_predict_batch_rejects_ragged_histories():
    torch = pytest.importorskip("torch")

    class FakeModel:
        def forecast(self, context, prediction_length):
            return None, torch.ones((context.shape[0], prediction_length), dtype=torch.float32)

    model = TiRexForecaster.__new__(TiRexForecaster)
    model._model = FakeModel()

    with pytest.raises(ValueError, match="equal-length histories"):
        model.predict_batch([np.arange(10), np.arange(9)], horizon=3)
