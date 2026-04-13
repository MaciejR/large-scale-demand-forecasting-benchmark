"""
WRMSSE — Weighted Root Mean Squared Scaled Error for the M5 competition.

Implements the full 12-level hierarchical metric defined in:
  Makridakis, Spiliotis, Assimakopoulos (2022) "M5 accuracy competition:
  Results, findings, and conclusions", International Journal of Forecasting.

For each of the 12 hierarchy levels the level score is

    level_score_l = Σ_i  w_i  *  RMSSE_i

where the weights w_i are each parent series' share of total dollar sales
in the last 28 days of the training period, and RMSSE_i is the
root-mean-squared scaled error of the parent series:

    RMSSE_i = sqrt( mean_t ((ŷ_i,t − y_i,t)^2 / scale_i^2) )

with scale_i = sqrt( mean_t in_train ((y_i,t − y_i,t-1)^2) ), the squared
first-difference average over the training window starting at the first
non-zero observation. The total WRMSSE is the unweighted mean over the
12 levels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


HIERARCHY_LEVELS = [
    [],
    ["state_id"],
    ["store_id"],
    ["cat_id"],
    ["dept_id"],
    ["state_id", "cat_id"],
    ["state_id", "dept_id"],
    ["store_id", "cat_id"],
    ["store_id", "dept_id"],
    ["item_id"],
    ["state_id", "item_id"],
    ["item_id", "store_id"],
]


def _build_meta(sales: pd.DataFrame) -> pd.DataFrame:
    """Return per-bottom-series hierarchy metadata."""
    return sales[
        ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
    ].astype(str).set_index("id")


def _last28_dollar_sales(
    sales: pd.DataFrame,
    calendar: pd.DataFrame,
    prices: pd.DataFrame,
    train_until: int,
) -> pd.Series:
    """Per-bottom-series dollar sales summed over the last 28 training days."""
    last28_d = list(range(train_until - 28 + 1, train_until + 1))
    last28_cols = [f"d_{i}" for i in last28_d]

    long = sales[["id", "item_id", "store_id"] + last28_cols].melt(
        id_vars=["id", "item_id", "store_id"],
        var_name="d_col",
        value_name="y",
    )
    long["d"] = long["d_col"].str.replace("d_", "", regex=False).astype(int)
    long = long.merge(calendar[["d", "wm_yr_wk"]], on="d", how="left")
    long = long.merge(
        prices[["item_id", "store_id", "wm_yr_wk", "sell_price"]],
        on=["item_id", "store_id", "wm_yr_wk"],
        how="left",
    )
    long["sell_price"] = long["sell_price"].fillna(0.0)
    long["dollar"] = long["y"] * long["sell_price"]
    return long.groupby("id")["dollar"].sum()


def _aggregate_to_level(
    bottom_wide: np.ndarray,
    meta: pd.DataFrame,
    series_order: list,
    level_keys: list[str],
) -> tuple[np.ndarray, list[str]]:
    """
    Aggregate a (n_bottom_series x T) wide array up to a parent level.

    Returns
    -------
    parent_wide : np.ndarray of shape (n_parent_series, T)
    parent_ids  : list of parent ids in the same order as parent_wide rows
    """
    if not level_keys:
        return bottom_wide.sum(axis=0, keepdims=True), ["__total__"]

    parent_id = meta.loc[series_order, level_keys].agg("__".join, axis=1).values
    df = pd.DataFrame(bottom_wide, index=parent_id)
    grouped = df.groupby(level=0).sum()
    return grouped.values, list(grouped.index)


def _series_rmsse(
    train_wide: np.ndarray,
    eval_true: np.ndarray,
    eval_pred: np.ndarray,
) -> np.ndarray:
    """
    Per-series RMSSE for any hierarchy level.

    train_wide : (n_parents, n_train_days)  used to compute scale_i
    eval_true  : (n_parents, n_eval_days)
    eval_pred  : (n_parents, n_eval_days)
    """
    diffs = np.diff(train_wide, axis=1)
    sq = diffs * diffs

    nz = train_wide > 0
    first_nz = np.where(nz.any(axis=1), nz.argmax(axis=1), train_wide.shape[1])
    n_parents = train_wide.shape[0]
    scales = np.empty(n_parents, dtype=np.float64)
    for i in range(n_parents):
        start = int(first_nz[i])
        if start >= sq.shape[1]:
            scales[i] = 1.0
            continue
        s = sq[i, start:].mean()
        scales[i] = max(np.sqrt(s), 1e-9)

    err = eval_true - eval_pred
    rmsse = np.sqrt((err * err).mean(axis=1)) / scales
    return rmsse


def compute_m5_wrmsse(
    results: pd.DataFrame,
    sales_path: str,
    calendar_path: str,
    prices_path: str,
    train_until: int,
) -> dict:
    """
    Compute the full 12-level WRMSSE for M5 from level-12 (item-store) predictions.

    Parameters
    ----------
    results : pd.DataFrame
        Level-12 predictions with columns:
          - series_id (must match M5 sales `id`)
          - y_true
          - y_pred
        Each series should appear in the same order across rows; rows are
        treated as consecutive eval-window timesteps.
    sales_path, calendar_path, prices_path : raw M5 file paths.
    train_until : int
        1-based exclusive index of the first eval day (i.e. number of
        training days used). Eval window is days [train_until+1, n_days].

    Returns
    -------
    dict with keys:
      - "WRMSSE": float (unweighted mean over levels)
      - "level_scores": dict[level_idx, float]
      - "level_n_series": dict[level_idx, int]
    """
    sales = pd.read_csv(sales_path)
    calendar = pd.read_csv(calendar_path)
    prices = pd.read_csv(prices_path)

    meta = _build_meta(sales)
    series_order = list(sales["id"])

    value_cols = [c for c in sales.columns if c.startswith("d_")]
    y_wide = sales[value_cols].values.astype(np.float64)
    n_series, n_days = y_wide.shape
    n_eval_days = n_days - train_until
    train_wide_bottom = y_wide[:, :train_until]

    pred_pivot = results.pivot_table(
        index="series_id", values=["y_true", "y_pred"],
        aggfunc=list,
    )
    eval_true_bottom = np.array([
        pred_pivot.loc[sid, "y_true"] for sid in series_order
    ], dtype=np.float64)
    eval_pred_bottom = np.array([
        pred_pivot.loc[sid, "y_pred"] for sid in series_order
    ], dtype=np.float64)

    if eval_true_bottom.shape[1] != n_eval_days:
        eval_true_bottom = eval_true_bottom[:, :n_eval_days]
        eval_pred_bottom = eval_pred_bottom[:, :n_eval_days]

    dollar_bottom = _last28_dollar_sales(sales, calendar, prices, train_until)
    dollar_bottom = dollar_bottom.reindex(series_order).fillna(0.0)
    dollar_arr = dollar_bottom.values

    level_scores = {}
    level_n_series = {}

    for li, keys in enumerate(HIERARCHY_LEVELS):
        train_l, parent_ids = _aggregate_to_level(
            train_wide_bottom, meta, series_order, keys
        )
        true_l, _ = _aggregate_to_level(
            eval_true_bottom, meta, series_order, keys
        )
        pred_l, _ = _aggregate_to_level(
            eval_pred_bottom, meta, series_order, keys
        )

        if not keys:
            dollar_l = np.array([dollar_arr.sum()])
        else:
            parent_id_per_bottom = (
                meta.loc[series_order, keys].agg("__".join, axis=1).values
            )
            dollar_df = pd.DataFrame({
                "parent": parent_id_per_bottom,
                "dollar": dollar_arr,
            }).groupby("parent")["dollar"].sum()
            dollar_l = dollar_df.reindex(parent_ids).fillna(0.0).values

        total = dollar_l.sum()
        weights = dollar_l / total if total > 0 else np.full_like(
            dollar_l, 1.0 / len(dollar_l)
        )

        rmsse = _series_rmsse(train_l, true_l, pred_l)
        level_score = float(np.nansum(weights * rmsse))
        level_scores[li + 1] = level_score
        level_n_series[li + 1] = train_l.shape[0]

    wrmsse = float(np.mean(list(level_scores.values())))
    return {
        "WRMSSE": wrmsse,
        "level_scores": level_scores,
        "level_n_series": level_n_series,
    }
