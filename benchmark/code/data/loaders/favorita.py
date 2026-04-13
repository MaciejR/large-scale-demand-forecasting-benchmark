"""
Favorita Grocery Sales Forecasting loader.

Source: Kaggle "favorita-grocery-sales-forecasting" competition (2018).
Corporación Favorita is an Ecuadorian retail chain. ~125k product-store
series at daily frequency over ~1700 days, with promotions, oil price,
and holidays as known covariates.

Files expected (CSV, in the same directory or supplied individually):
- train.csv          : id, date, store_nbr, item_nbr, unit_sales, onpromotion
- stores.csv         : store_nbr, city, state, type, cluster
- items.csv          : item_nbr, family, class, perishable
- transactions.csv   : date, store_nbr, transactions
- oil.csv            : date, dcoilwtico
- holidays_events.csv: date, type, locale, locale_name, description, transferred

Returns the unified long-format dataframe used across this benchmark:
  [series_id, ds, y] (+ KNOWN_DYNAMIC_COLUMNS when with_covariates=True)
where series_id = "{store_nbr}_{item_nbr}" and y = unit_sales.
"""

import os
import pandas as pd


KNOWN_DYNAMIC_COLUMNS = [
    "onpromotion",
    "dcoilwtico",
    "is_holiday",
    "transactions",
    "dayofweek",
    "month",
]


def load_favorita(
    path_train: str,
    path_oil: str | None = None,
    path_holidays: str | None = None,
    path_stores: str | None = None,
    path_transactions: str | None = None,
    with_covariates: bool = False,
    max_series: int | None = None,
) -> pd.DataFrame:
    """
    Load Favorita into a long-format DataFrame.

    Parameters
    ----------
    path_train : str
        Path to train.csv.
    path_oil, path_holidays, path_stores, path_transactions : str, optional
        Required only when with_covariates=True.
    with_covariates : bool
        If True, joins onpromotion, oil price, holiday flag, store
        transactions, and calendar features.
    max_series : int, optional
        Cap series count for development. Picks the most-active series.

    Returns
    -------
    pd.DataFrame with [series_id, ds, y] and KNOWN_DYNAMIC_COLUMNS when
    with_covariates=True.
    """
    train = pd.read_csv(
        path_train,
        usecols=["date", "store_nbr", "item_nbr", "unit_sales", "onpromotion"],
        parse_dates=["date"],
        dtype={"store_nbr": "int16", "item_nbr": "int32"},
    )
    train["unit_sales"] = train["unit_sales"].clip(lower=0.0).astype("float32")
    train["series_id"] = (
        train["store_nbr"].astype(str) + "_" + train["item_nbr"].astype(str)
    )

    if max_series:
        top = (
            train.groupby("series_id")["unit_sales"].sum()
            .nlargest(max_series).index
        )
        train = train[train["series_id"].isin(top)]

    df = train.rename(columns={"date": "ds", "unit_sales": "y"})

    if not with_covariates:
        return df[["series_id", "ds", "y"]]

    df["onpromotion"] = df["onpromotion"].fillna(False).astype("int8")

    if path_oil:
        oil = pd.read_csv(path_oil, parse_dates=["date"])
        oil["dcoilwtico"] = oil["dcoilwtico"].ffill().bfill().astype("float32")
        df = df.merge(oil.rename(columns={"date": "ds"}), on="ds", how="left")
        df["dcoilwtico"] = df["dcoilwtico"].fillna(method="ffill").fillna(0.0)
    else:
        df["dcoilwtico"] = 0.0

    if path_holidays:
        hol = pd.read_csv(path_holidays, parse_dates=["date"])
        hol = hol[hol["transferred"] == False]
        hol_dates = set(hol["date"].unique())
        df["is_holiday"] = df["ds"].isin(hol_dates).astype("int8")
    else:
        df["is_holiday"] = 0

    if path_transactions:
        tx = pd.read_csv(path_transactions, parse_dates=["date"])
        df = df.merge(
            tx.rename(columns={"date": "ds"}),
            on=["ds", "store_nbr"], how="left",
        )
        df["transactions"] = df["transactions"].fillna(0.0).astype("float32")
    else:
        df["transactions"] = 0.0

    df["dayofweek"] = df["ds"].dt.dayofweek.astype("int8")
    df["month"] = df["ds"].dt.month.astype("int8")

    out_cols = ["series_id", "ds", "y"] + KNOWN_DYNAMIC_COLUMNS
    return df[out_cols]
