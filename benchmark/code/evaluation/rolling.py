"""
Rolling-origin evaluation.
"""

import pandas as pd
from typing import Callable


def rolling_forecast(
    df: pd.DataFrame,
    horizon: int,
    min_train_size: int,
    forecast_fn: Callable,
):
    """
    df: DataFrame with columns [series_id, ds, y]
    forecast_fn: function(train_series, horizon) -> pd.Series
    """
    outputs = []

    for sid, g in df.groupby("series_id"):
        g = g.sort_values("ds")
        y = g["y"].reset_index(drop=True)

        for t in range(min_train_size, len(y) - horizon + 1, horizon):
            train = y.iloc[:t]
            test = y.iloc[t : t + horizon]
            pred = forecast_fn(train, horizon)

            for i in range(horizon):
                outputs.append(
                    {
                        "series_id": sid,
                        "y_true": test.iloc[i],
                        "y_pred": pred.iloc[i],
                    }
                )

    return pd.DataFrame(outputs)
