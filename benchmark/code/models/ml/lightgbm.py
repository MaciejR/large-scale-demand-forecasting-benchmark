"""
Global LightGBM model for demand forecasting.
Uses lagged features and rolling statistics.
"""

import pandas as pd
import lightgbm as lgb


def make_features(df: pd.DataFrame, lags=(1, 7, 14), windows=(7, 14)):
    df = df.copy()
    for lag in lags:
        df[f"lag_{lag}"] = df.groupby("series_id")["y"].shift(lag)
    for w in windows:
        df[f"roll_mean_{w}"] = (
            df.groupby("series_id")["y"].shift(1).rolling(w).mean()
        )
    return df


class LightGBMForecaster:
    def __init__(self, params=None):
        self.params = params or {
            "objective": "regression",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "verbosity": -1,
        }
        self.model = None

    def fit(self, df: pd.DataFrame):
        df_feat = make_features(df).dropna()
        X = df_feat.drop(columns=["series_id", "ds", "y"])
        y = df_feat["y"]
        self.model = lgb.LGBMRegressor(**self.params)
        self.model.fit(X, y)

    def predict(self, history: pd.DataFrame, horizon: int) -> pd.Series:
        preds = []
        hist = history.copy()
        for _ in range(horizon):
            feat = make_features(hist).iloc[-1:]
            X = feat.drop(columns=["series_id", "ds", "y"])
            y_hat = self.model.predict(X)[0]
            preds.append(y_hat)
            new_row = hist.iloc[-1:].copy()
            new_row["y"] = y_hat
            hist = pd.concat([hist, new_row], ignore_index=True)
        return pd.Series(preds)
