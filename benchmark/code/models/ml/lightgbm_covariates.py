"""
Covariate-aware LightGBM forecaster.
Extends the global LightGBM approach with exogenous features (price, promo, etc.).
"""

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor


def _make_features_with_covariates(
    df: pd.DataFrame,
    covariate_columns: list[str],
    lags: tuple = (1, 7, 14),
    windows: tuple = (7, 14),
) -> pd.DataFrame:
    """Create lag, rolling, and covariate features."""
    df = df.copy()

    # Lag features (per series)
    for lag in lags:
        df[f"lag_{lag}"] = df.groupby("series_id")["y"].shift(lag)

    # Rolling mean features (per series)
    for w in windows:
        df[f"roll_mean_{w}"] = (
            df.groupby("series_id")["y"]
            .transform(lambda x: x.shift(1).rolling(w).mean())
        )

    # Day-of-week feature
    if pd.api.types.is_datetime64_any_dtype(df["ds"]):
        df["dayofweek"] = df["ds"].dt.dayofweek

    feature_cols = (
        [f"lag_{l}" for l in lags]
        + [f"roll_mean_{w}" for w in windows]
        + ["dayofweek"]
        + covariate_columns
    )

    return df, feature_cols


class LightGBMCovariateForecaster:
    """Global LightGBM model that uses exogenous covariates."""

    def __init__(self, covariate_columns: list[str], params: dict = None):
        self.covariate_columns = covariate_columns
        self.params = params or {
            "objective": "regression",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "verbosity": -1,
            "n_estimators": 200,
        }
        self.model_ = None
        self._feature_cols = None

    def fit(self, df: pd.DataFrame):
        """
        Fit on all series globally.

        Parameters
        ----------
        df : pd.DataFrame
            Columns: [series_id, ds, y] + self.covariate_columns
        """
        df_feat, self._feature_cols = _make_features_with_covariates(
            df, self.covariate_columns
        )
        df_feat = df_feat.dropna(subset=self._feature_cols)

        X = df_feat[self._feature_cols].values
        y = df_feat["y"].values

        self.model_ = LGBMRegressor(**self.params)
        self.model_.fit(X, y)

    def predict(
        self,
        history: pd.DataFrame,
        horizon: int,
        future_covariates: pd.DataFrame = None,
    ) -> pd.Series:
        """
        Autoregressive prediction with covariates.

        Parameters
        ----------
        history : pd.DataFrame
            Past data for ONE series: [series_id, ds, y] + covariates.
        horizon : int
            Steps ahead.
        future_covariates : pd.DataFrame
            Covariate values for the forecast period. Shape (horizon, n_covariates).
            Columns must match self.covariate_columns.

        Returns
        -------
        pd.Series of length `horizon`.
        """
        hist = history.copy().sort_values("ds").reset_index(drop=True)
        preds = []

        for h in range(horizon):
            row_features = {}

            # Lags
            for lag in (1, 7, 14):
                idx = len(hist) - lag
                row_features[f"lag_{lag}"] = hist["y"].iloc[idx] if idx >= 0 else np.nan

            # Rolling means
            for w in (7, 14):
                vals = hist["y"].iloc[-(w + 1):-1] if len(hist) > w else hist["y"]
                row_features[f"roll_mean_{w}"] = vals.mean()

            # Day of week
            if pd.api.types.is_datetime64_any_dtype(hist["ds"]):
                last_ds = hist["ds"].iloc[-1]
                next_ds = last_ds + pd.Timedelta(days=1)
                row_features["dayofweek"] = next_ds.dayofweek
            else:
                row_features["dayofweek"] = 0

            # Covariates from future
            for col in self.covariate_columns:
                if future_covariates is not None and col in future_covariates.columns:
                    row_features[col] = future_covariates[col].iloc[h]
                else:
                    row_features[col] = 0.0

            X = np.array([[row_features[c] for c in self._feature_cols]])
            pred = self.model_.predict(X)[0]
            preds.append(pred)

            # Append prediction to history for next step
            new_row = {"series_id": hist["series_id"].iloc[0], "y": pred}
            if pd.api.types.is_datetime64_any_dtype(hist["ds"]):
                new_row["ds"] = hist["ds"].iloc[-1] + pd.Timedelta(days=1)
            else:
                new_row["ds"] = len(hist)
            for col in self.covariate_columns:
                new_row[col] = row_features[col]
            hist = pd.concat([hist, pd.DataFrame([new_row])], ignore_index=True)

        return pd.Series(preds)
