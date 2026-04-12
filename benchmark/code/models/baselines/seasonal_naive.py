"""
Seasonal Naive forecaster.
Repeats the last full seasonal cycle forward.
"""

import numpy as np
import pandas as pd


def seasonal_naive_forecast(
    train: pd.Series, horizon: int, season_length: int = 7
) -> pd.Series:
    """
    Forecast by repeating the last `season_length` observations.

    Parameters
    ----------
    train : pd.Series
        Historical values.
    horizon : int
        Number of steps to forecast.
    season_length : int
        Length of the seasonal cycle (default 7 for daily data with weekly pattern).

    Returns
    -------
    pd.Series of length `horizon`.
    """
    last_season = train.iloc[-season_length:].values
    reps = int(np.ceil(horizon / season_length))
    tiled = np.tile(last_season, reps)[:horizon]
    return pd.Series(tiled)
