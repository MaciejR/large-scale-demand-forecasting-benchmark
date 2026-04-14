"""
M5 dataset loader.
Loads and preprocesses M5 data into a unified long-format dataframe.
"""

import pandas as pd


KNOWN_DYNAMIC_COLUMNS = [
    "sell_price",
    "snap_CA",
    "snap_TX",
    "snap_WI",
    "is_event",
    "wday",
    "month",
]


def load_m5(
    path_sales: str,
    path_calendar: str,
    path_prices: str | None = None,
    with_covariates: bool = False,
) -> pd.DataFrame:
    """
    Load M5 into a long-format DataFrame.

    Parameters
    ----------
    path_sales : str
        Path to sales_train_validation.csv.
    path_calendar : str
        Path to calendar.csv (must contain SNAP / event columns when
        with_covariates=True).
    path_prices : str, optional
        Path to sell_prices.csv. Required when with_covariates=True.
    with_covariates : bool
        If True, returns the columns listed in KNOWN_DYNAMIC_COLUMNS in
        addition to [series_id, ds, y].

    Returns
    -------
    pd.DataFrame
        Always contains [series_id, ds, y]. When with_covariates=True,
        also contains the columns in KNOWN_DYNAMIC_COLUMNS.
    """
    sales = pd.read_csv(path_sales)
    calendar = pd.read_csv(path_calendar)
    calendar["d"] = calendar["d"].str.replace("d_", "").astype(int)

    value_cols = [c for c in sales.columns if c.startswith("d_")]
    id_vars = ["id"]
    if with_covariates:
        id_vars += ["item_id", "store_id"]

    df = sales.melt(
        id_vars=id_vars,
        value_vars=value_cols,
        var_name="d",
        value_name="y",
    )
    df["d"] = df["d"].str.replace("d_", "").astype(int)

    if not with_covariates:
        df = df.merge(calendar[["d", "date"]], on="d", how="left")
        df = df.rename(columns={"id": "series_id", "date": "ds"})
        df["ds"] = pd.to_datetime(df["ds"])
        return df[["series_id", "ds", "y"]]

    cal_cols = [
        "d", "date", "wm_yr_wk", "wday", "month",
        "snap_CA", "snap_TX", "snap_WI",
        "event_type_1", "event_type_2",
    ]
    df = df.merge(calendar[cal_cols], on="d", how="left")
    df = df.rename(columns={"id": "series_id", "date": "ds"})
    df["ds"] = pd.to_datetime(df["ds"])

    df["is_event"] = (
        df["event_type_1"].notna() | df["event_type_2"].notna()
    ).astype("int8")
    df = df.drop(columns=["event_type_1", "event_type_2"])

    prices = pd.read_csv(path_prices)
    df = df.merge(
        prices, on=["store_id", "item_id", "wm_yr_wk"], how="left"
    )
    df["sell_price"] = df["sell_price"].astype("float32").fillna(0.0)

    out_cols = ["series_id", "ds", "y"] + KNOWN_DYNAMIC_COLUMNS
    return df[out_cols]
