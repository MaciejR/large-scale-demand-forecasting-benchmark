"""
Chronos-Bolt-Tiny (AWS) zero-shot forecaster for the local sensitivity run.

Reference: A11 (AWS 2024) — Chronos-Bolt family, T5-based encoder-only
architecture. Tiny is the smallest public variant (~9 M params), chosen
for local MacBook inference via PyTorch MPS where larger variants
either exceed unified memory or drop off the consumer-box cost frontier
we are trying to measure in §6.5.

Requires: pip install "chronos-forecasting>=1.4"

Device note: MPS is supported by the underlying transformers T5 stack
in PyTorch 2.3+. If MPS fails on a specific kernel we fall back to CPU
with a warning rather than failing the whole sweep.
"""

import numpy as np
import pandas as pd


class ChronosBoltTinyForecaster:
    """Wrapper for AWS Chronos-Bolt-Tiny zero-shot point forecasting."""

    def __init__(
        self,
        model_id: str = "amazon/chronos-bolt-tiny",
        device: str = "mps",
    ):
        self.model_id = model_id
        self.device = device
        self._pipeline = None

    def _load_model(self):
        if self._pipeline is None:
            from chronos import BaseChronosPipeline

            try:
                self._pipeline = BaseChronosPipeline.from_pretrained(
                    self.model_id,
                    device_map=self.device,
                )
            except (RuntimeError, NotImplementedError) as err:
                if self.device == "mps":
                    print(
                        f"WARNING: Chronos-Bolt-Tiny MPS load failed ({err}); "
                        f"falling back to CPU."
                    )
                    self.device = "cpu"
                    self._pipeline = BaseChronosPipeline.from_pretrained(
                        self.model_id,
                        device_map="cpu",
                    )
                else:
                    raise

    def predict(self, train: pd.Series, horizon: int) -> pd.Series:
        """Zero-shot point forecast (median over 20 samples)."""
        import torch

        self._load_model()
        inputs = torch.tensor(train.values, dtype=torch.float32).unsqueeze(0)

        quantiles, mean = self._pipeline.predict_quantiles(
            inputs=inputs,
            prediction_length=horizon,
            quantile_levels=[0.1, 0.5, 0.9],
        )
        median = quantiles[0, :, 1]
        if hasattr(median, "cpu"):
            median = median.cpu()
        return pd.Series(median.numpy())

    def predict_batch(
        self,
        histories,
        horizon: int,
        quantile_levels: list[float] | None = None,
    ) -> tuple[np.ndarray, dict[float, np.ndarray]]:
        """Batched zero-shot forecast returning mean and requested quantiles."""
        import torch

        self._load_model()
        levels = quantile_levels or [0.1, 0.5, 0.9]
        arrays = [np.asarray(hist, dtype=np.float32) for hist in histories]
        if not arrays:
            return np.empty((0, horizon), dtype=np.float32), {}
        max_len = max(len(arr) for arr in arrays)
        padded = np.full((len(arrays), max_len), np.nan, dtype=np.float32)
        for row_idx, arr in enumerate(arrays):
            padded[row_idx, -len(arr) :] = arr

        inputs = torch.tensor(padded, dtype=torch.float32)
        quantiles, mean = self._pipeline.predict_quantiles(
            inputs=inputs,
            prediction_length=horizon,
            quantile_levels=levels,
        )
        if hasattr(mean, "cpu"):
            mean = mean.cpu()
        if hasattr(quantiles, "cpu"):
            quantiles = quantiles.cpu()
        mean_arr = np.asarray(mean, dtype=np.float32)[:, :horizon]
        quantile_arr = np.asarray(quantiles, dtype=np.float32)[:, :horizon, :]
        return mean_arr, {
            level: quantile_arr[:, :, idx]
            for idx, level in enumerate(levels)
        }
