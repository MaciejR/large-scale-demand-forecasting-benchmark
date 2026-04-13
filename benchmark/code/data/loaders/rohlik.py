"""
Rohlik Sales Forecasting Challenge v2 loader.

Source: Kaggle "rohlik-sales-forecasting-challenge-v2" (2024). Rohlik is
a CZ/HU/AT/DE/RO online grocery delivery company. The v2 release is at
the SKU x warehouse level, ~5–6k unique series, daily frequency over
~700 days. Calendar covariates include holidays, school holidays, and
sell-price.

Files expected:
- sales_train.csv : unique_id, warehouse, date, sales, sell_price_main,
                    type, name, L1_..., L2_..., L3_..., L4_category_name_en,
                    holiday, holiday_name, shops_closed,
                    winter_school_holidays, school_holidays, weight,
                    availability

Returns the unified long-format dataframe used across this benchmark:
  [series_id, ds, y] (+ KNOWN_DYNAMIC_COLUMNS when with_covariates=True)
where series_id = unique_id and y = sales.
"""

import pandas as pd


KNOWN_DYNAMIC_COLUMNS = [
    "sell_price_main",
    "holiday",
    "shops_closed",
    "winter_school_holidays",
    "school_holidays",
    "dayofweek",
    "month",
]


def load_rohlik(
    path_train: str,
    path_calendar: str | None = None,
    with_covariates: bool = False,
    max_series: int | None = None,
) -> pd.DataFrame:
    """
    Load Rohlik Sales Forecasting Challenge v2 into a long-format DataFrame.

    Parameters
    ----------
    path_train : str
        Path to sales_train.csv (cols: unique_id, date, warehouse, sales,
        sell_price_main, availability, type_0..6_discount).
    path_calendar : str, optional
        Path to calendar.csv (cols: date, warehouse, holiday, shops_closed,
        winter_school_holidays, school_holidays). Only used when
        with_covariates=True. If None, calendar covariates default to 0.
    with_covariates : bool
        If True, returns KNOWN_DYNAMIC_COLUMNS in addition to [series_id,
        ds, y].
    max_series : int, optional
        Cap series count for development. Picks the most-active series.
    """
    base_cols = ["unique_id", "date", "sales"]
    sales_cov_cols = ["warehouse", "sell_price_main", "availability"]
    use_cols = base_cols + (sales_cov_cols if with_covariates else [])

    df = pd.read_csv(path_train, usecols=use_cols, parse_dates=["date"])
    df = df.rename(columns={
        "unique_id": "series_id",
        "date": "ds",
        "sales": "y",
    })
    df["y"] = df["y"].clip(lower=0.0).astype("float32")

    if max_series:
        top = (
            df.groupby("series_id")["y"].sum()
            .nlargest(max_series).index
        )
        df = df[df["series_id"].isin(top)]

    if not with_covariates:
        return df[["series_id", "ds", "y"]]

    df["sell_price_main"] = df["sell_price_main"].fillna(0).astype("float32")

    cal_keys = ["holiday", "shops_closed", "winter_school_holidays", "school_holidays"]
    if path_calendar:
        cal = pd.read_csv(
            path_calendar,
            usecols=["date", "warehouse"] + cal_keys,
            parse_dates=["date"],
        ).rename(columns={"date": "ds"})
        for c in cal_keys:
            cal[c] = cal[c].fillna(0).astype("float32")
        df = df.merge(cal, on=["ds", "warehouse"], how="left")
    for c in cal_keys:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = df[c].fillna(0).astype("float32")

    df["dayofweek"] = df["ds"].dt.dayofweek.astype("int8")
    df["month"] = df["ds"].dt.month.astype("int8")

    out_cols = ["series_id", "ds", "y"] + KNOWN_DYNAMIC_COLUMNS
    return df[out_cols]
