"""
ETS forecasting baseline using statsmodels.
"""

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def ets_forecast(train: pd.Series, horizon: int) -> pd.Series:
    model = ExponentialSmoothing(
        train,
        trend=None,
        seasonal="add",
        seasonal_periods=7,
    )
    fitted = model.fit(optimized=True)
    return fitted.forecast(horizon)
