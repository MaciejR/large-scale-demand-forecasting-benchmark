"""
fev-bench dataset loader — Retail domain tasks.
Loads data into [series_id, ds, y, ...covariates] format.
Requires: pip install fev
"""

import pandas as pd


RETAIL_TASKS = [
    "rohlik_sales_1D",
    "rohlik_sales_1W",
    "rohlik_orders_1D",
    "rohlik_orders_1W",
    "rossmann_1D",
    "rossmann_1W",
    "restaurant",
    "hermes",
    "walmart",
    "m5_1D",
    "m5_1W",
    "m5_1M",
    "hierarchical_sales_1D",
    "hierarchical_sales_1W",
    "favorita_stores_1D",
    "favorita_stores_1W",
    "favorita_stores_1M",
    "favorita_transactions_1D",
    "favorita_transactions_1W",
    "favorita_transactions_1M",
]

COVARIATE_TASKS = [
    "rohlik_sales_1D",
    "rohlik_sales_1W",
    "rohlik_orders_1D",
    "rohlik_orders_1W",
    "rossmann_1D",
    "rossmann_1W",
    "hermes",
    "walmart",
    "m5_1D",
    "m5_1W",
    "m5_1M",
    "favorita_stores_1D",
    "favorita_stores_1W",
    "favorita_stores_1M",
    "favorita_transactions_1D",
    "favorita_transactions_1W",
    "favorita_transactions_1M",
]

_TASK_DEFS = {
    "m5_1D": {
        "horizon": 28,
        "seasonality": 7,
        "num_windows": 1,
        "known_dynamic_columns": [
            "sell_price", "event_National", "event_Religious",
            "event_Cultural", "snap_CA", "event_Sporting", "snap_WI", "snap_TX",
        ],
        "static_columns": ["item_id", "dept_id", "cat_id", "store_id", "state_id"],
    },
    "m5_1W": {
        "horizon": 13,
        "seasonality": 4,
        "num_windows": 1,
        "known_dynamic_columns": [
            "sell_price", "event_National", "event_Religious",
            "event_Cultural", "snap_CA", "event_Sporting", "snap_WI", "snap_TX",
        ],
        "static_columns": ["item_id", "dept_id", "cat_id", "store_id", "state_id"],
    },
    "m5_1M": {
        "horizon": 12,
        "seasonality": 12,
        "num_windows": 1,
        "known_dynamic_columns": [
            "sell_price", "event_National", "event_Religious",
            "event_Cultural", "snap_CA", "event_Sporting", "snap_WI", "snap_TX",
        ],
        "static_columns": ["item_id", "dept_id", "cat_id", "store_id", "state_id"],
    },
    "favorita_stores_1D": {
        "target": "sales",
        "horizon": 28,
        "seasonality": 7,
        "num_windows": 10,
        "known_dynamic_columns": ["holiday", "onpromotion"],
        "past_dynamic_columns": ["oil_price"],
        "static_columns": ["store_nbr", "family", "city", "state", "type", "cluster"],
    },
    "favorita_stores_1W": {
        "target": "sales",
        "horizon": 13,
        "seasonality": 4,
        "num_windows": 10,
        "known_dynamic_columns": ["onpromotion"],
        "past_dynamic_columns": ["oil_price"],
        "static_columns": ["store_nbr", "family", "city", "state", "type", "cluster"],
    },
    "favorita_stores_1M": {
        "target": "sales",
        "horizon": 12,
        "seasonality": 12,
        "num_windows": 2,
        "known_dynamic_columns": ["onpromotion"],
        "past_dynamic_columns": ["oil_price"],
        "static_columns": ["store_nbr", "family", "city", "state", "type", "cluster"],
    },
    "favorita_transactions_1D": {
        "target": "transactions",
        "horizon": 28,
        "seasonality": 7,
        "num_windows": 10,
        "known_dynamic_columns": ["holiday"],
        "past_dynamic_columns": ["oil_price"],
        "static_columns": ["store_nbr", "city", "state", "type", "cluster"],
    },
    "favorita_transactions_1W": {
        "target": "transactions",
        "horizon": 13,
        "seasonality": 4,
        "num_windows": 10,
        "known_dynamic_columns": [],
        "past_dynamic_columns": ["oil_price"],
        "static_columns": ["store_nbr", "city", "state", "type", "cluster"],
    },
    "favorita_transactions_1M": {
        "target": "transactions",
        "horizon": 12,
        "seasonality": 12,
        "num_windows": 2,
        "known_dynamic_columns": [],
        "past_dynamic_columns": ["oil_price"],
        "static_columns": ["store_nbr", "city", "state", "type", "cluster"],
    },
    "rossmann_1D": {
        "target": "Sales",
        "horizon": 48,
        "seasonality": 7,
        "num_windows": 10,
        "known_dynamic_columns": ["SchoolHoliday", "Promo", "DayOfWeek", "Open", "StateHoliday"],
        "past_dynamic_columns": ["Customers"],
        "static_columns": ["Store", "StoreType", "Assortment", "CompetitionDistance"],
    },
    "rossmann_1W": {
        "target": "Sales",
        "horizon": 13,
        "seasonality": 4,
        "num_windows": 8,
        "known_dynamic_columns": ["Open", "SchoolHoliday", "StateHoliday", "Promo"],
        "past_dynamic_columns": ["Customers"],
        "static_columns": ["Store", "StoreType", "Assortment", "CompetitionDistance"],
    },
    "rohlik_sales_1D": {
        "target": "sales",
        "horizon": 14,
        "seasonality": 7,
        "num_windows": 1,
        "known_dynamic_columns": [
            "total_orders", "sell_price_main", "holiday",
            "shops_closed", "winter_school_holidays", "school_holidays",
        ],
        "past_dynamic_columns": ["availability"],
        "static_columns": ["product_unique_id", "warehouse"],
    },
    "rohlik_sales_1W": {
        "target": "sales",
        "horizon": 8,
        "seasonality": 4,
        "num_windows": 1,
        "known_dynamic_columns": [
            "total_orders", "sell_price_main", "holiday",
            "shops_closed", "winter_school_holidays", "school_holidays",
        ],
        "past_dynamic_columns": ["availability"],
        "static_columns": ["product_unique_id", "warehouse"],
    },
    "rohlik_orders_1D": {
        "target": "orders",
        "horizon": 61,
        "seasonality": 7,
        "num_windows": 5,
        "known_dynamic_columns": ["holiday", "shops_closed", "winter_school_holidays", "school_holidays"],
        "past_dynamic_columns": ["shutdown", "mini_shutdown", "precipitation", "snow"],
        "static_columns": [],
    },
    "rohlik_orders_1W": {
        "target": "orders",
        "horizon": 8,
        "seasonality": 4,
        "num_windows": 5,
        "known_dynamic_columns": ["holiday", "shops_closed", "winter_school_holidays", "school_holidays"],
        "past_dynamic_columns": ["shutdown", "mini_shutdown", "precipitation", "snow"],
        "static_columns": [],
    },
    "restaurant": {
        "horizon": 28,
        "seasonality": 7,
        "num_windows": 8,
        "known_dynamic_columns": [],
        "static_columns": ["air_genre_name", "air_area_name"],
    },
    "hermes": {
        "horizon": 52,
        "seasonality": 52,
        "num_windows": 1,
        "known_dynamic_columns": ["external"],
        "static_columns": ["country", "category"],
    },
    "walmart": {
        "horizon": 39,
        "seasonality": 52,
        "num_windows": 1,
        "known_dynamic_columns": [
            "MarkDown1", "MarkDown2", "MarkDown3", "MarkDown4", "MarkDown5",
            "Unemployment", "Fuel_Price", "Temperature", "CPI", "IsHoliday",
        ],
        "static_columns": ["Store", "Dept", "Type", "Size"],
    },
    "hierarchical_sales_1D": {
        "horizon": 28,
        "seasonality": 7,
        "num_windows": 10,
        "known_dynamic_columns": [],
        "static_columns": [],
    },
    "hierarchical_sales_1W": {
        "horizon": 13,
        "seasonality": 4,
        "num_windows": 10,
        "known_dynamic_columns": [],
        "static_columns": [],
    },
}


def load_fev_bench_task(
    task_name: str,
    window_idx: int = 0,
) -> tuple[pd.DataFrame, dict]:
    """
    Load a fev-bench task and convert to long format.

    Parameters
    ----------
    task_name : str
        One of RETAIL_TASKS (e.g. "m5_1D", "favorita_stores_1D").
    window_idx : int
        Which evaluation window to load (0-based). Default 0 = first window.

    Returns
    -------
    tuple of (df, metadata):
        df: pd.DataFrame with columns [series_id, ds, y, ...covariates]
        metadata: dict with keys horizon, seasonality, num_windows, covariate_columns
    """
    import fev

    task_def = _TASK_DEFS[task_name]
    known_dynamic = task_def.get("known_dynamic_columns", [])
    past_dynamic = task_def.get("past_dynamic_columns", [])
    static_cols = task_def.get("static_columns", [])

    task = fev.Task(
        dataset_path="autogluon/fev_datasets",
        dataset_config=task_name,
        horizon=task_def["horizon"],
        num_windows=task_def["num_windows"],
        seasonality=task_def["seasonality"],
        eval_metric="SQL",
        quantile_levels=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
        target=task_def.get("target", "target"),
        known_dynamic_columns=known_dynamic,
        past_dynamic_columns=past_dynamic,
        static_columns=static_cols,
    )

    windows = list(task.iter_windows())
    window = windows[window_idx]
    past_df, future_df, static_df = fev.convert_input_data(window, adapter="pandas")

    # Rename to standard format
    target_col = task.target if isinstance(task.target, str) else task.target[0]
    rename_map = {"id": "series_id", "timestamp": "ds"}
    if target_col != "y":
        rename_map[target_col] = "y"
    past_df = past_df.rename(columns=rename_map)

    metadata = {
        "horizon": task_def["horizon"],
        "seasonality": task_def["seasonality"],
        "num_windows": task_def["num_windows"],
        "known_dynamic_columns": known_dynamic,
        "past_dynamic_columns": past_dynamic,
        "static_columns": static_cols,
        "task_name": task_name,
    }

    return past_df, metadata
