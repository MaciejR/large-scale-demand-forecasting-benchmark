"""
Evaluation metrics for demand forecasting.
All metrics are computed per series and then aggregated.
"""

import numpy as np
import pandas as pd


def mae(y_true, y_pred):
    return np.mean(np.abs(y_true - y_pred))


def smape(y_true, y_pred):
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom = np.where(denom == 0, 1e-8, denom)
    return np.mean(np.abs(y_true - y_pred) / denom) * 100


def wape(y_true, y_pred):
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true))


def aggregate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expects columns: [series_id, y_true, y_pred]
    """
    results = []
    for sid, g in df.groupby("series_id"):
        y_t = g["y_true"].values
        y_p = g["y_pred"].values
        results.append(
            {
                "series_id": sid,
                "MAE": mae(y_t, y_p),
                "sMAPE": smape(y_t, y_p),
                "WAPE": wape(y_t, y_p),
            }
        )
    return pd.DataFrame(results)
