"""
TimesFM 2.5 (Google) foundation model wrapper.
Zero-shot time series forecasting with continuous quantile head.

TimesFM 2.5 (~200 M params, decoder-only) is the largest FM in scope.
The PyTorch variant runs on CPU; MPS support is experimental. On a
16 GB MacBook this is the most memory-constrained model — if it OOMs,
reduce max_context.

Requires: pip install timesfm>=2.0
"""

import numpy as np
import pandas as pd


class TimesFM25Forecaster:
    """Wrapper for Google TimesFM 2.5 zero-shot forecasting."""

    def __init__(
        self,
        model_id: str = "google/timesfm-2.5-200m-pytorch",
        max_context: int = 1024,
        device: str = "cpu",
    ):
        self.model_id = model_id
        self.max_context = max_context
        # TimesFM PyTorch variant: CPU is the safest default. MPS may work
        # for the core matmuls but the quantile head uses ops that can fail
        # on Apple Silicon. Override via device="mps" at your own risk.
        self.device = device
        self._model = None

    def _load_model(self):
        if self._model is None:
            import torch
            import timesfm

            torch.set_float32_matmul_precision("high")
            try:
                self._model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
                    self.model_id
                )
                self._model.compile(
                    timesfm.ForecastConfig(
                        max_context=self.max_context,
                        max_horizon=256,
                        normalize_inputs=True,
                        use_continuous_quantile_head=True,
                        force_flip_invariance=True,
                        infer_is_positive=True,
                        fix_quantile_crossing=True,
                    )
                )
            except Exception as err:
                print(f"WARNING: TimesFM 2.5 load/compile failed: {err}")
                raise

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
        pd.Series of length `horizon`.
        """
        self._load_model()

        values = train.values.astype(np.float64)
        if len(values) > self.max_context:
            values = values[-self.max_context:]

        point_forecast, quantile_forecast = self._model.forecast(
            horizon=horizon,
            inputs=[values],
        )
        return pd.Series(point_forecast[0][:horizon])

    def predict_quantiles(
        self, train: pd.Series, horizon: int
    ) -> pd.DataFrame:
        """
        Probabilistic forecast returning quantile predictions.

        Returns DataFrame with columns for each quantile level.
        """
        self._load_model()

        values = train.values.astype(np.float64)
        if len(values) > self.max_context:
            values = values[-self.max_context:]

        point_forecast, quantile_forecast = self._model.forecast(
            horizon=horizon,
            inputs=[values],
        )

        df = pd.DataFrame(quantile_forecast[0][:horizon])
        df.columns = [f"q{i}" for i in range(df.shape[1])]
        df["point"] = point_forecast[0][:horizon]
        return df
