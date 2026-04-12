"""
Chronos-2 (Amazon) foundation model wrapper.
Zero-shot time series forecasting.
Requires: pip install "chronos-forecasting[extras]>=2.2"
"""

import numpy as np
import pandas as pd


class Chronos2Forecaster:
    """Wrapper for Amazon Chronos-2 zero-shot forecasting."""

    def __init__(
        self,
        model_id: str = "amazon/chronos-2",
        device: str = "cuda",
    ):
        self.model_id = model_id
        self.device = device
        self._pipeline = None

    def _load_model(self):
        if self._pipeline is None:
            from chronos import BaseChronosPipeline

            self._pipeline = BaseChronosPipeline.from_pretrained(
                self.model_id,
                device_map=self.device,
            )

    def predict(self, train: pd.Series, horizon: int) -> pd.Series:
        """
        Zero-shot point forecast.

        Parameters
        ----------
        train : pd.Series
            Historical values.
        horizon : int
            Number of steps to forecast.

        Returns
        -------
        pd.Series of length `horizon` (median forecast).
        """
        import torch

        self._load_model()

        context = torch.tensor(train.values, dtype=torch.float32)
        quantiles, mean = self._pipeline.predict_quantiles(
            context=context,
            prediction_length=horizon,
            quantile_levels=[0.1, 0.5, 0.9],
        )
        point_forecast = mean[0].numpy()
        return pd.Series(point_forecast)

    def predict_quantiles(
        self, train: pd.Series, horizon: int, levels: list[float] = None
    ) -> pd.DataFrame:
        """
        Probabilistic forecast returning quantiles.

        Returns DataFrame with columns named by quantile level.
        """
        import torch

        self._load_model()
        if levels is None:
            levels = [0.1, 0.25, 0.5, 0.75, 0.9]

        context = torch.tensor(train.values, dtype=torch.float32)
        quantiles, mean = self._pipeline.predict_quantiles(
            context=context,
            prediction_length=horizon,
            quantile_levels=levels,
        )

        df = pd.DataFrame(
            quantiles[0].numpy(),
            columns=[f"q{q}" for q in levels],
        )
        df["mean"] = mean[0].numpy()
        return df
