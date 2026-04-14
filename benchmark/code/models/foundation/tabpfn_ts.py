"""
TabPFN-TS (PriorLabs) zero-shot forecaster for the local sensitivity run.

Reference: A14 (PriorLabs 2025) — TabPFN-TS wraps the tabular
foundation model TabPFN with a time-series head. ~11 M parameters,
covariate-aware, and the only model in our local sweep that can
consume future-known covariates (§5.1.1) end-to-end.

License: PriorLabs RL-NC (non-commercial). Reproducible for research;
not deployable without a commercial license. §5.4.5 documents this as
a deployability caveat on the consumer-box sensitivity panel.

Requires: pip install "tabpfn-time-series>=0.2"

Device note: we force local on-device inference (no PriorLabs cloud
round-trip) so the machine fingerprint for §5.4.5 actually reflects
the work being done on the MacBook and not on PriorLabs' servers.
"""

import numpy as np
import pandas as pd


class TabPFNTSForecaster:
    """Wrapper for TabPFN-TS zero-shot point forecasting."""

    def __init__(self, device: str = "mps"):
        self.device = device
        self._pipeline = None

    def _load_model(self):
        if self._pipeline is None:
            from tabpfn_time_series import TabPFNTSPipeline, TabPFNMode

            self._pipeline = TabPFNTSPipeline(tabpfn_mode=TabPFNMode.LOCAL)

    def predict(self, train: pd.Series, horizon: int) -> pd.Series:
        """Zero-shot point forecast. Univariate call path."""
        self._load_model()

        n = len(train)
        context_df = pd.DataFrame(
            {
                "item_id": "series",
                "timestamp": pd.date_range("2000-01-01", periods=n, freq="D"),
                "target": train.values.astype("float32"),
            }
        )

        pred_df = self._pipeline.predict_df(context_df, prediction_length=horizon)
        if "target" in pred_df.columns:
            point = pred_df["target"].values
        elif "0.5" in pred_df.columns:
            point = pred_df["0.5"].values
        else:
            point = pred_df.iloc[:, -1].values
        return pd.Series(np.asarray(point)[:horizon])
