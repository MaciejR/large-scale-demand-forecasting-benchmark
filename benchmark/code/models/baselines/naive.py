"""
Naive forecasting baseline.
"""

import pandas as pd


def naive_forecast(train: pd.Series, horizon: int) -> pd.Series:
    last_value = train.iloc[-1]
    return pd.Series([last_value] * horizon)
