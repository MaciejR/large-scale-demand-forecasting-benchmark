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

Device note: TabPFN's transformer backbone supports MPS. Covariate
handling is done by the wrapper's own preprocessor which runs on CPU
regardless of backbone device; this is fine for our inference budget.
"""

import numpy as np
import pandas as pd


class TabPFNTSForecaster:
    """Wrapper for TabPFN-TS zero-shot point forecasting."""

    def __init__(self, device: str = "mps"):
        self.device = device
        self._predictor = None

    def _load_model(self):
        if self._predictor is None:
            from tabpfn_time_series import TabPFNTimeSeriesPredictor

            try:
                self._predictor = TabPFNTimeSeriesPredictor(device=self.device)
            except (RuntimeError, NotImplementedError, TypeError) as err:
                if self.device == "mps":
                    print(
                        f"WARNING: TabPFN-TS MPS init failed ({err}); "
                        f"falling back to CPU."
                    )
                    self.device = "cpu"
                    self._predictor = TabPFNTimeSeriesPredictor(device="cpu")
                else:
                    raise

    def predict(self, train: pd.Series, horizon: int) -> pd.Series:
        """Zero-shot point forecast. Univariate call path."""
        self._load_model()

        n = len(train)
        history = pd.DataFrame(
            {
                "unique_id": "series",
                "ds": pd.date_range("2000-01-01", periods=n, freq="D"),
                "target": train.values.astype("float32"),
            }
        )
        future_ds = pd.date_range(
            start=history["ds"].iloc[-1] + pd.Timedelta(days=1),
            periods=horizon,
            freq="D",
        )
        future = pd.DataFrame({"unique_id": "series", "ds": future_ds})

        pred_df = self._predictor.predict(history, future)
        point = pred_df["target"].values if "target" in pred_df.columns else pred_df.iloc[:, -1].values
        return pd.Series(point[:horizon])
