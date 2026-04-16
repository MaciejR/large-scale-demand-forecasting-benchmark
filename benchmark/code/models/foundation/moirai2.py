"""
Moirai 2.0 (Salesforce) foundation model wrapper.
Zero-shot any-variate time series forecasting.

Moirai-2.0-R-Small (~11 M params, decoder-only MoE) is the smallest
variant. On MPS the model loads but inference may be slow due to
MoE routing on non-CUDA devices. Falls back to CPU if MPS fails.

Requires: pip install uni2ts
"""

import numpy as np
import pandas as pd


class Moirai2Forecaster:
    """Wrapper for Salesforce Moirai 2.0 zero-shot forecasting."""

    def __init__(
        self,
        model_id: str = "Salesforce/moirai-2.0-R-small",
        device: str = "mps",
        context_length: int = 512,
        num_samples: int = 100,
    ):
        self.model_id = model_id
        self.device = device
        self.context_length = context_length
        self.num_samples = num_samples
        self._model = None
        self._current_horizon = None

    def _load_model(self, horizon: int):
        """Lazy load model with specific horizon."""
        import torch
        from uni2ts.model.moirai2 import Moirai2Forecast, Moirai2Module

        # Determine actual device — MPS may not support all ops.
        actual_device = self.device
        try:
            module = Moirai2Module.from_pretrained(self.model_id)
            self._model = Moirai2Forecast(
                module=module,
                prediction_length=horizon,
                context_length=self.context_length,
                target_dim=1,
                feat_dynamic_real_dim=0,
                past_feat_dynamic_real_dim=0,
            )
            # Quick smoke test on MPS.
            if actual_device == "mps":
                test_input = torch.zeros(1, min(10, self.context_length), 1)
                with torch.no_grad():
                    _ = self._model.predict(test_input)
        except (RuntimeError, NotImplementedError) as err:
            if actual_device == "mps":
                print(
                    f"WARNING: Moirai 2.0 MPS failed ({err}); "
                    f"falling back to CPU."
                )
                self.device = "cpu"
                module = Moirai2Module.from_pretrained(self.model_id)
                self._model = Moirai2Forecast(
                    module=module,
                    prediction_length=horizon,
                    context_length=self.context_length,
                    target_dim=1,
                    feat_dynamic_real_dim=0,
                    past_feat_dynamic_real_dim=0,
                )
            else:
                raise
        self._current_horizon = horizon

    def predict(self, train: pd.Series, horizon: int) -> pd.Series:
        """
        Zero-shot point forecast (median of sampled trajectories).

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
        import torch
        from einops import rearrange

        if self._model is None or self._current_horizon != horizon:
            self._load_model(horizon)

        values = train.values.astype(np.float32)
        if len(values) > self.context_length:
            values = values[-self.context_length:]

        past_target = rearrange(
            torch.as_tensor(values, dtype=torch.float32),
            "t -> 1 t 1",
        )

        with torch.no_grad():
            forecast_samples = self._model.predict(past_target)

        samples = forecast_samples.squeeze().numpy()
        if samples.ndim == 1:
            point_forecast = samples
        else:
            point_forecast = np.median(samples, axis=0)

        return pd.Series(point_forecast[:horizon])

    def predict_quantiles(
        self, train: pd.Series, horizon: int, levels: list[float] = None
    ) -> pd.DataFrame:
        """Probabilistic forecast via sample quantiles."""
        import torch
        from einops import rearrange

        if self._model is None or self._current_horizon != horizon:
            self._load_model(horizon)
        if levels is None:
            levels = [0.1, 0.25, 0.5, 0.75, 0.9]

        values = train.values.astype(np.float32)
        if len(values) > self.context_length:
            values = values[-self.context_length:]

        past_target = rearrange(
            torch.as_tensor(values, dtype=torch.float32),
            "t -> 1 t 1",
        )

        with torch.no_grad():
            forecast_samples = self._model.predict(past_target)

        samples = forecast_samples.squeeze().numpy()
        if samples.ndim == 1:
            samples = samples.reshape(1, -1)

        df = pd.DataFrame({
            f"q{q}": np.quantile(samples, q, axis=0)[:horizon]
            for q in levels
        })
        df["median"] = np.median(samples, axis=0)[:horizon]
        return df
