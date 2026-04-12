"""
M5 dataset loader.
Loads and preprocesses M5 data into a unified long-format dataframe.
"""

import pandas as pd


def load_m5(path_sales: str, path_calendar: str) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
    [series_id, ds, y]
    """
    sales = pd.read_csv(path_sales)
    calendar = pd.read_csv(path_calendar)

    value_cols = [c for c in sales.columns if c.startswith("d_")]
    df = sales.melt(
        id_vars=["id"],
        value_vars=value_cols,
        var_name="d",
        value_name="y",
    )

    df["d"] = df["d"].str.replace("d_", "").astype(int)
    df = df.merge(calendar[["d", "date"]], on="d", how="left")
    df = df.rename(columns={"id": "series_id", "date": "ds"})
    df["ds"] = pd.to_datetime(df["ds"])

    return df[["series_id", "ds", "y"]]
