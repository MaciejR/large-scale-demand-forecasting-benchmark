"""
Chronos-2 (Amazon) foundation model wrapper.
Zero-shot time series forecasting with optional covariate support.

Chronos-2 (~120 M params, encoder-only T5 with input tokenization)
is the only FM in scope that natively supports covariates. The
covariate path uses the DataFrame-based predict API introduced in
chronos-forecasting v2.2.

Requires: pip install "chronos-forecasting[extras]>=2.2"

Device note: MPS is supported via the T5 backbone in PyTorch 2.3+.
Falls back to CPU if MPS fails (same pattern as chronos_bolt_tiny.py).
"""

import numpy as np
import pandas as pd


class Chronos2Forecaster:
    """Wrapper for Amazon Chronos-2 zero-shot forecasting."""

    def __init__(
        self,
        model_id: str = "amazon/chronos-2",
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
                        f"WARNING: Chronos-2 MPS load failed ({err}); "
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
        """
        Zero-shot univariate point forecast (median).

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

        self._load_model()
        # Chronos-2 expects 3D: (n_series, n_variates, history_length)
        context = torch.tensor(
            train.values, dtype=torch.float32
        ).reshape(1, 1, -1)

        quantiles_list, mean_list = self._pipeline.predict_quantiles(
            inputs=context,
            prediction_length=horizon,
            quantile_levels=[0.1, 0.5, 0.9],
        )
        # quantiles_list[0] shape: (n_series=1, prediction_length, n_quantiles)
        # q0.5 is at quantile index 1.
        q_tensor = quantiles_list[0]
        median = q_tensor[0, :, 1]  # (prediction_length,)
        if hasattr(median, "cpu"):
            median = median.cpu()
        return pd.Series(median.numpy()[:horizon])

    def predict_with_covariates(
        self,
        target: pd.Series,
        covariates: pd.DataFrame,
        horizon: int,
        future_covariates: pd.DataFrame = None,
    ) -> pd.Series:
        """
        Zero-shot forecast with covariates via Chronos-2 input tokenization.

        Chronos-2 is the only FM in our scope that natively consumes
        covariates — all others are univariate-only. This method uses the
        DataFrame-based predict API from chronos-forecasting >= 2.2.

        Parameters
        ----------
        target : pd.Series
            Historical target values (length T).
        covariates : pd.DataFrame
            Historical covariate values (shape T x n_covariates).
        horizon : int
            Number of steps to forecast.
        future_covariates : pd.DataFrame, optional
            Future-known covariate values (shape horizon x n_covariates).
            If provided, concatenated to extend the covariate context.

        Returns
        -------
        pd.Series of length `horizon`.
        """
        import torch

        self._load_model()

        # Build context DataFrame: target + covariate columns.
        context_df = covariates.copy()
        context_df["target"] = target.values

        if future_covariates is not None:
            # Append future-known covariates with NaN target (to be predicted).
            future_df = future_covariates.copy()
            future_df["target"] = np.nan
            context_df = pd.concat([context_df, future_df], ignore_index=True)

        # Chronos-2 predict_quantiles with DataFrame context.
        # The pipeline auto-detects covariate columns (non-target).
        quantiles_list, mean_list = self._pipeline.predict_quantiles(
            inputs=context_df,
            prediction_length=horizon,
            quantile_levels=[0.1, 0.5, 0.9],
        )
        q_tensor = quantiles_list[0]
        # Shape may be (1, pred_len, n_q) or (pred_len, n_q)
        if q_tensor.ndim == 3:
            median = q_tensor[0, :, 1]
        else:
            median = q_tensor[:, 1]
        if hasattr(median, "cpu"):
            median = median.cpu()
        return pd.Series(median.numpy()[:horizon])

    def predict_quantiles(
        self, train: pd.Series, horizon: int, levels: list[float] = None
    ) -> pd.DataFrame:
        """Probabilistic forecast returning quantiles."""
        import torch

        self._load_model()
        if levels is None:
            levels = [0.1, 0.25, 0.5, 0.75, 0.9]

        context = torch.tensor(
            train.values, dtype=torch.float32
        ).reshape(1, 1, -1)
        quantiles_list, mean_list = self._pipeline.predict_quantiles(
            inputs=context,
            prediction_length=horizon,
            quantile_levels=levels,
        )

        # Shape: (n_series=1, prediction_length, n_quantiles)
        q_tensor = quantiles_list[0][0]  # (prediction_length, n_quantiles)
        q_arr = q_tensor.cpu().numpy() if hasattr(q_tensor, "cpu") else np.asarray(q_tensor)
        df = pd.DataFrame(q_arr[:horizon], columns=[f"q{q}" for q in levels])
        m_tensor = mean_list[0][0]  # (prediction_length,)
        m_arr = m_tensor.cpu().numpy() if hasattr(m_tensor, "cpu") else np.asarray(m_tensor)
        df["mean"] = m_arr[:horizon]
        return df
