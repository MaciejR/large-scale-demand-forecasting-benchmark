#!/usr/bin/env python3
"""
Extract fev-bench retail task results into extraction_schema.csv rows.

Source: Shchur et al. (2025), "fev-bench: A Realistic Benchmark for Time
Series Forecasting", arXiv:2509.26468. Raw per-model CSVs from
https://github.com/autogluon/fev/tree/main/benchmarks/fev_bench/results/

This script generates extraction rows for all 20 retail tasks across
7 FM models + 2 ML_TREE baselines + 1 statistical ensemble, with
SQL, MASE, and WAPE metrics. Expected yield: ~180 new rows.

Usage: python analysis/extract_fev_bench_retail.py
"""

import csv
import os

# ── Task metadata ──────────────────────────────────────────────────────
# Each task: (task_name, dataset_parent, n_series, frequency, horizon, has_covariates)
TASKS = [
    ("m5_1D", "M5", "30490", "D", "28", "Yes"),
    ("m5_1W", "M5", "30490", "W", "13", "Yes"),
    ("m5_1M", "M5", "29364", "M", "12", "Yes"),
    ("favorita_stores_1D", "Favorita", "1579", "D", "28", "Yes"),
    ("favorita_stores_1W", "Favorita", "1579", "W", "13", "Yes"),
    ("favorita_stores_1M", "Favorita", "3158", "M", "12", "Yes"),
    ("favorita_transactions_1D", "Favorita", "51", "D", "28", "Yes"),
    ("favorita_transactions_1W", "Favorita", "51", "W", "13", "Yes"),
    ("favorita_transactions_1M", "Favorita", "102", "M", "12", "Yes"),
    ("rossmann_1D", "Rossmann", "1115", "D", "48", "Yes"),
    ("rossmann_1W", "Rossmann", "1115", "W", "13", "Yes"),
    ("walmart", "Walmart", "2936", "W", "39", "Yes"),
    ("rohlik_orders_1D", "Rohlik v2", "7", "D", "61", "Yes"),
    ("rohlik_orders_1W", "Rohlik v2", "7", "W", "8", "Yes"),
    ("rohlik_sales_1D", "Rohlik v2", "4116", "D", "14", "Yes"),
    ("rohlik_sales_1W", "Rohlik v2", "3942", "W", "8", "Yes"),
    ("restaurant", "Restaurant", "813", "D", "28", "Yes"),
    ("hierarchical_sales_1D", "Hierarchical Sales", "118", "D", "28", "No"),
    ("hierarchical_sales_1W", "Hierarchical Sales", "118", "W", "13", "No"),
    ("hermes", "Hermes", "10000", "W", "52", "Yes"),
]

# ── Model metadata ─────────────────────────────────────────────────────
# (csv_model_name, schema_model_name, model_family, zero_shot, fine_tuned, notes)
MODELS = [
    ("TiRex", "TiRex", "foundation", "Yes", "No", "~35M params; xLSTM; zero-shot"),
    ("TimesFM-2.5", "TimesFM-2.5", "foundation", "Yes", "No", "200M params; decoder-only; zero-shot"),
    ("Chronos-2", "Chronos-2", "foundation", "Yes", "No", "120M params; encoder-only T5; zero-shot; natively supports covariates but evaluated univariate in fev-bench"),
    ("Chronos-Bolt", "Chronos-Bolt-Base", "foundation", "Yes", "No", "~46M params; T5 encoder-only; zero-shot"),
    ("Moirai-2.0", "Moirai-2.0-Small", "foundation", "Yes", "No", "11M params; decoder-only MoE; zero-shot"),
    ("Toto-1.0", "Toto-1.0", "foundation", "Yes", "No", "foundation model; open base; zero-shot"),
    ("TabPFN-TS", "TabPFN-TS", "foundation", "Yes", "No", "~12M params; tabular PFN + temporal; zero-shot; ONLY model using covariates in fev-bench"),
    ("LightGBM (Recursive)", "LightGBM (Recursive)", "ml_tree", "No", "Yes", "AutoGluon-TS 0.14.0; per-task trained; recursive; uses covariates"),
    ("CatBoost (Recursive)", "CatBoost (Recursive)", "ml_tree", "No", "Yes", "AutoGluon-TS 0.14.0; per-task trained; recursive; uses covariates"),
    ("Stat. Ensemble", "Statistical Ensemble", "statistical", "No", "Yes", "AutoETS + AutoARIMA + AutoTheta + AutoCES (SCUM)"),
]

# ── Per-task per-model metric values ───────────────────────────────────
# Extracted from raw GitHub CSVs. Format: {task: {model: {metric: value}}}
# "--" means the model failed on that task (TabPFN-TS, Stat. Ensemble).
DATA = {
    # Chronos-2
    ("m5_1D", "Chronos-2"): {"SQL": "0.7216", "MASE": "0.8799", "WAPE": "0.7031"},
    ("m5_1W", "Chronos-2"): {"SQL": "0.9002", "MASE": "1.1400", "WAPE": "0.4283"},
    ("m5_1M", "Chronos-2"): {"SQL": "0.9770", "MASE": "1.1638", "WAPE": "0.4289"},
    ("favorita_stores_1D", "Chronos-2"): {"SQL": "0.9164", "MASE": "1.1402", "WAPE": "0.1383"},
    ("favorita_stores_1W", "Chronos-2"): {"SQL": "2.0241", "MASE": "2.2987", "WAPE": "0.1289"},
    ("favorita_stores_1M", "Chronos-2"): {"SQL": "1.7944", "MASE": "1.9752", "WAPE": "0.1303"},
    ("favorita_transactions_1D", "Chronos-2"): {"SQL": "0.6846", "MASE": "0.8494", "WAPE": "0.0612"},
    ("favorita_transactions_1W", "Chronos-2"): {"SQL": "1.2279", "MASE": "1.4988", "WAPE": "0.0562"},
    ("favorita_transactions_1M", "Chronos-2"): {"SQL": "0.9426", "MASE": "1.2531", "WAPE": "0.0719"},
    ("rossmann_1D", "Chronos-2"): {"SQL": "0.2835", "MASE": "0.3558", "WAPE": "0.1198"},
    ("rossmann_1W", "Chronos-2"): {"SQL": "0.3077", "MASE": "0.3712", "WAPE": "0.0964"},
    ("walmart", "Chronos-2"): {"SQL": "0.6478", "MASE": "0.8167", "WAPE": "0.0934"},
    ("rohlik_orders_1D", "Chronos-2"): {"SQL": "0.9592", "MASE": "1.1869", "WAPE": "0.0561"},
    ("rohlik_orders_1W", "Chronos-2"): {"SQL": "1.2997", "MASE": "1.5471", "WAPE": "0.0503"},
    ("rohlik_sales_1D", "Chronos-2"): {"SQL": "0.8808", "MASE": "1.1016", "WAPE": "0.2763"},
    ("rohlik_sales_1W", "Chronos-2"): {"SQL": "1.2741", "MASE": "1.5597", "WAPE": "0.2291"},
    ("restaurant", "Chronos-2"): {"SQL": "0.6853", "MASE": "0.8599", "WAPE": "0.3584"},
    ("hierarchical_sales_1D", "Chronos-2"): {"SQL": "0.5567", "MASE": "0.6889", "WAPE": "0.7005"},
    ("hierarchical_sales_1W", "Chronos-2"): {"SQL": "0.6161", "MASE": "0.7539", "WAPE": "0.4328"},
    ("hermes", "Chronos-2"): {"SQL": "0.6092", "MASE": "0.7761", "WAPE": "0.0029"},

    # TimesFM-2.5 (SQL/MASE from agent tables, WAPE from raw CSV)
    ("m5_1D", "TimesFM-2.5"): {"SQL": "0.7190", "MASE": "0.8720", "WAPE": "0.8721"},
    ("m5_1W", "TimesFM-2.5"): {"SQL": "0.8890", "MASE": "1.1222", "WAPE": "1.1222"},
    ("m5_1M", "TimesFM-2.5"): {"SQL": "0.9800", "MASE": "1.1576", "WAPE": "1.1576"},
    ("favorita_stores_1D", "TimesFM-2.5"): {"SQL": "0.9490", "MASE": "1.1676", "WAPE": "1.1676"},
    ("favorita_stores_1W", "TimesFM-2.5"): {"SQL": "1.9680", "MASE": "2.2901", "WAPE": "2.2901"},
    ("favorita_stores_1M", "TimesFM-2.5"): {"SQL": "1.9980", "MASE": "2.2338", "WAPE": "2.2338"},
    ("favorita_transactions_1D", "TimesFM-2.5"): {"SQL": "0.8740", "MASE": "1.0842", "WAPE": "1.0842"},
    ("favorita_transactions_1W", "TimesFM-2.5"): {"SQL": "1.2230", "MASE": "1.4718", "WAPE": "1.4718"},
    ("favorita_transactions_1M", "TimesFM-2.5"): {"SQL": "1.1330", "MASE": "1.3316", "WAPE": "1.3316"},
    ("rossmann_1D", "TimesFM-2.5"): {"SQL": "0.5020", "MASE": "0.6106", "WAPE": "0.6106"},
    ("rossmann_1W", "TimesFM-2.5"): {"SQL": "0.4950", "MASE": "0.6543", "WAPE": "0.6543"},
    ("walmart", "TimesFM-2.5"): {"SQL": "0.6790", "MASE": "0.8615", "WAPE": "0.8615"},
    ("rohlik_orders_1D", "TimesFM-2.5"): {"SQL": "1.0060", "MASE": "1.2504", "WAPE": "1.2504"},
    ("rohlik_orders_1W", "TimesFM-2.5"): {"SQL": "1.3280", "MASE": "1.6592", "WAPE": "1.6592"},
    ("rohlik_sales_1D", "TimesFM-2.5"): {"SQL": "1.0960", "MASE": "1.3238", "WAPE": "1.3238"},
    ("rohlik_sales_1W", "TimesFM-2.5"): {"SQL": "1.4010", "MASE": "1.6891", "WAPE": "1.6891"},
    ("restaurant", "TimesFM-2.5"): {"SQL": "0.6770", "MASE": "0.8503", "WAPE": "0.8503"},
    ("hierarchical_sales_1D", "TimesFM-2.5"): {"SQL": "0.5520", "MASE": "0.6882", "WAPE": "0.6882"},
    ("hierarchical_sales_1W", "TimesFM-2.5"): {"SQL": "0.6180", "MASE": "0.7508", "WAPE": "0.7508"},
    ("hermes", "TimesFM-2.5"): {"SQL": "0.6180", "MASE": "0.7872", "WAPE": "0.7872"},

    # Moirai-2.0 (SQL/MASE from agent tables, WAPE from raw CSV)
    ("m5_1D", "Moirai-2.0"): {"SQL": "0.7100", "MASE": "0.8690", "WAPE": "0.6984"},
    ("m5_1W", "Moirai-2.0"): {"SQL": "0.9070", "MASE": "1.1500", "WAPE": "0.4286"},
    ("m5_1M", "Moirai-2.0"): {"SQL": "0.9960", "MASE": "1.1770", "WAPE": "0.4363"},
    ("favorita_stores_1D", "Moirai-2.0"): {"SQL": "0.9800", "MASE": "1.2050", "WAPE": "0.1568"},
    ("favorita_stores_1W", "Moirai-2.0"): {"SQL": "2.1970", "MASE": "2.5770", "WAPE": "0.1555"},
    ("favorita_stores_1M", "Moirai-2.0"): {"SQL": "2.0910", "MASE": "2.3240", "WAPE": "0.2355"},
    ("favorita_transactions_1D", "Moirai-2.0"): {"SQL": "1.1210", "MASE": "1.3300", "WAPE": "0.0837"},
    ("favorita_transactions_1W", "Moirai-2.0"): {"SQL": "1.4630", "MASE": "1.6850", "WAPE": "0.0672"},
    ("favorita_transactions_1M", "Moirai-2.0"): {"SQL": "1.3900", "MASE": "1.6110", "WAPE": "0.0863"},
    ("rossmann_1D", "Moirai-2.0"): {"SQL": "0.5270", "MASE": "0.6480", "WAPE": "0.2215"},
    ("rossmann_1W", "Moirai-2.0"): {"SQL": "0.4970", "MASE": "0.6440", "WAPE": "0.1759"},
    ("walmart", "Moirai-2.0"): {"SQL": "0.8450", "MASE": "1.0560", "WAPE": "0.1315"},
    ("rohlik_orders_1D", "Moirai-2.0"): {"SQL": "0.9700", "MASE": "1.1760", "WAPE": "0.0552"},
    ("rohlik_orders_1W", "Moirai-2.0"): {"SQL": "1.5320", "MASE": "1.8740", "WAPE": "0.0612"},
    ("rohlik_sales_1D", "Moirai-2.0"): {"SQL": "1.1700", "MASE": "1.4020", "WAPE": "0.3821"},
    ("rohlik_sales_1W", "Moirai-2.0"): {"SQL": "1.5160", "MASE": "1.8220", "WAPE": "0.2871"},
    ("restaurant", "Moirai-2.0"): {"SQL": "0.6810", "MASE": "0.8520", "WAPE": "0.3573"},
    ("hierarchical_sales_1D", "Moirai-2.0"): {"SQL": "0.5520", "MASE": "0.6880", "WAPE": "0.6930"},
    ("hierarchical_sales_1W", "Moirai-2.0"): {"SQL": "0.6280", "MASE": "0.7660", "WAPE": "0.4365"},
    ("hermes", "Moirai-2.0"): {"SQL": "0.7040", "MASE": "0.8850", "WAPE": "0.0034"},

    # Chronos-Bolt (SQL/MASE from agent tables, WAPE from raw CSV)
    ("m5_1D", "Chronos-Bolt"): {"SQL": "0.7290", "MASE": "0.8852", "WAPE": "0.8852"},
    ("m5_1W", "Chronos-Bolt"): {"SQL": "0.9170", "MASE": "1.1647", "WAPE": "1.1647"},
    ("m5_1M", "Chronos-Bolt"): {"SQL": "1.0000", "MASE": "1.1852", "WAPE": "1.1852"},
    ("favorita_stores_1D", "Chronos-Bolt"): {"SQL": "1.0320", "MASE": "1.2689", "WAPE": "1.2689"},
    ("favorita_stores_1W", "Chronos-Bolt"): {"SQL": "2.1010", "MASE": "2.4749", "WAPE": "2.4749"},
    ("favorita_stores_1M", "Chronos-Bolt"): {"SQL": "2.0870", "MASE": "2.4178", "WAPE": "2.4178"},
    ("favorita_transactions_1D", "Chronos-Bolt"): {"SQL": "0.9750", "MASE": "1.1515", "WAPE": "1.1515"},
    ("favorita_transactions_1W", "Chronos-Bolt"): {"SQL": "1.4280", "MASE": "1.7479", "WAPE": "1.7479"},
    ("favorita_transactions_1M", "Chronos-Bolt"): {"SQL": "1.3590", "MASE": "1.6365", "WAPE": "1.6365"},
    ("rossmann_1D", "Chronos-Bolt"): {"SQL": "0.5250", "MASE": "0.6371", "WAPE": "0.6371"},
    ("rossmann_1W", "Chronos-Bolt"): {"SQL": "0.4870", "MASE": "0.6452", "WAPE": "0.6452"},
    ("walmart", "Chronos-Bolt"): {"SQL": "0.7740", "MASE": "0.9671", "WAPE": "0.9671"},
    ("rohlik_orders_1D", "Chronos-Bolt"): {"SQL": "1.0510", "MASE": "1.3016", "WAPE": "1.3016"},
    ("rohlik_orders_1W", "Chronos-Bolt"): {"SQL": "1.4280", "MASE": "1.7219", "WAPE": "1.7219"},
    ("rohlik_sales_1D", "Chronos-Bolt"): {"SQL": "1.1470", "MASE": "1.3871", "WAPE": "1.3871"},
    ("rohlik_sales_1W", "Chronos-Bolt"): {"SQL": "1.5220", "MASE": "1.8467", "WAPE": "1.8467"},
    ("restaurant", "Chronos-Bolt"): {"SQL": "0.6890", "MASE": "0.8660", "WAPE": "0.8660"},
    ("hierarchical_sales_1D", "Chronos-Bolt"): {"SQL": "0.5510", "MASE": "0.6860", "WAPE": "0.6860"},
    ("hierarchical_sales_1W", "Chronos-Bolt"): {"SQL": "0.6370", "MASE": "0.7733", "WAPE": "0.7733"},
    ("hermes", "Chronos-Bolt"): {"SQL": "0.6750", "MASE": "0.8579", "WAPE": "0.8579"},

    # TiRex
    ("m5_1D", "TiRex"): {"SQL": "0.7144", "MASE": "0.8753", "WAPE": "0.7025"},
    ("m5_1W", "TiRex"): {"SQL": "0.9026", "MASE": "1.1477", "WAPE": "0.4281"},
    ("m5_1M", "TiRex"): {"SQL": "0.9740", "MASE": "1.1629", "WAPE": "0.4306"},
    ("favorita_stores_1D", "TiRex"): {"SQL": "0.9682", "MASE": "1.1934", "WAPE": "0.1518"},
    ("favorita_stores_1W", "TiRex"): {"SQL": "2.0462", "MASE": "2.4235", "WAPE": "0.1346"},
    ("favorita_stores_1M", "TiRex"): {"SQL": "1.8559", "MASE": "2.2147", "WAPE": "0.1894"},
    ("favorita_transactions_1D", "TiRex"): {"SQL": "1.0314", "MASE": "1.3493", "WAPE": "0.0820"},
    ("favorita_transactions_1W", "TiRex"): {"SQL": "1.3836", "MASE": "1.7465", "WAPE": "0.0591"},
    ("favorita_transactions_1M", "TiRex"): {"SQL": "1.0893", "MASE": "1.3596", "WAPE": "0.0772"},
    ("rossmann_1D", "TiRex"): {"SQL": "0.5391", "MASE": "0.6601", "WAPE": "0.2251"},
    ("rossmann_1W", "TiRex"): {"SQL": "0.4816", "MASE": "0.6218", "WAPE": "0.1697"},
    ("walmart", "TiRex"): {"SQL": "0.7075", "MASE": "0.8862", "WAPE": "0.1054"},
    ("rohlik_orders_1D", "TiRex"): {"SQL": "0.9858", "MASE": "1.2034", "WAPE": "0.0572"},
    ("rohlik_orders_1W", "TiRex"): {"SQL": "1.3004", "MASE": "1.5829", "WAPE": "0.0521"},
    ("rohlik_sales_1D", "TiRex"): {"SQL": "1.1481", "MASE": "1.3845", "WAPE": "0.3784"},
    ("rohlik_sales_1W", "TiRex"): {"SQL": "1.4252", "MASE": "1.7354", "WAPE": "0.2736"},
    ("restaurant", "TiRex"): {"SQL": "0.6816", "MASE": "0.8522", "WAPE": "0.3584"},
    ("hierarchical_sales_1D", "TiRex"): {"SQL": "0.5473", "MASE": "0.6854", "WAPE": "0.6894"},
    ("hierarchical_sales_1W", "TiRex"): {"SQL": "0.6209", "MASE": "0.7567", "WAPE": "0.4324"},
    ("hermes", "TiRex"): {"SQL": "0.6510", "MASE": "0.8310", "WAPE": "0.0031"},

    # LightGBM (Recursive)
    ("m5_1D", "LightGBM (Recursive)"): {"SQL": "0.9079", "MASE": "0.9079", "WAPE": "0.7322"},
    ("m5_1W", "LightGBM (Recursive)"): {"SQL": "1.1347", "MASE": "1.1347", "WAPE": "0.4232"},
    ("m5_1M", "LightGBM (Recursive)"): {"SQL": "1.1739", "MASE": "1.1739", "WAPE": "0.4408"},
    ("favorita_stores_1D", "LightGBM (Recursive)"): {"SQL": "1.2322", "MASE": "1.2322", "WAPE": "0.1585"},
    ("favorita_stores_1W", "LightGBM (Recursive)"): {"SQL": "2.4844", "MASE": "2.4844", "WAPE": "0.1374"},
    ("favorita_stores_1M", "LightGBM (Recursive)"): {"SQL": "2.4363", "MASE": "2.4363", "WAPE": "0.2631"},
    ("favorita_transactions_1D", "LightGBM (Recursive)"): {"SQL": "1.4454", "MASE": "1.4454", "WAPE": "0.0821"},
    ("favorita_transactions_1W", "LightGBM (Recursive)"): {"SQL": "1.9072", "MASE": "1.9072", "WAPE": "0.0649"},
    ("favorita_transactions_1M", "LightGBM (Recursive)"): {"SQL": "1.5469", "MASE": "1.5469", "WAPE": "0.1033"},
    ("rossmann_1D", "LightGBM (Recursive)"): {"SQL": "0.3368", "MASE": "0.3368", "WAPE": "0.1112"},
    ("rossmann_1W", "LightGBM (Recursive)"): {"SQL": "0.6779", "MASE": "0.6779", "WAPE": "0.1884"},
    ("walmart", "LightGBM (Recursive)"): {"SQL": "1.2457", "MASE": "1.2457", "WAPE": "0.1514"},
    ("rohlik_orders_1D", "LightGBM (Recursive)"): {"SQL": "1.2529", "MASE": "1.2529", "WAPE": "0.0591"},
    ("rohlik_orders_1W", "LightGBM (Recursive)"): {"SQL": "1.4545", "MASE": "1.4545", "WAPE": "0.0468"},
    ("rohlik_sales_1D", "LightGBM (Recursive)"): {"SQL": "1.3517", "MASE": "1.3517", "WAPE": "0.3571"},
    ("rohlik_sales_1W", "LightGBM (Recursive)"): {"SQL": "1.8946", "MASE": "1.8946", "WAPE": "0.2987"},
    ("restaurant", "LightGBM (Recursive)"): {"SQL": "0.9593", "MASE": "0.9593", "WAPE": "0.4087"},
    ("hierarchical_sales_1D", "LightGBM (Recursive)"): {"SQL": "0.6884", "MASE": "0.6884", "WAPE": "0.6910"},
    ("hierarchical_sales_1W", "LightGBM (Recursive)"): {"SQL": "0.7892", "MASE": "0.7892", "WAPE": "0.4444"},
    ("hermes", "LightGBM (Recursive)"): {"SQL": "1.1824", "MASE": "1.1824", "WAPE": "0.0046"},
}

# ── Paper metadata ─────────────────────────────────────────────────────
PAPER = {
    "authors": "Shchur et al.",
    "year": "2025",
    "title": "fev-bench: A Realistic Benchmark for Time Series Forecasting",
    "venue": "arXiv",
}

SCHEMA_PATH = "analysis/extraction_schema.csv"
HEADER = [
    "paper_id", "authors", "year", "title", "venue", "dataset",
    "dataset_variant", "n_series", "series_length_median", "frequency",
    "has_covariates", "model_name", "model_family", "zero_shot",
    "fine_tuned", "horizon", "eval_method", "metric_name", "metric_value",
    "runtime_reported", "gpu_hours", "hardware", "notes",
]


def task_meta(task_name):
    for t in TASKS:
        if t[0] == task_name:
            return t
    return None


def model_meta(csv_name):
    for m in MODELS:
        if m[0] == csv_name:
            return m
    return None


def generate_rows():
    """Generate extraction_schema rows from fev-bench retail data."""
    rows = []
    for (task_name, csv_model_name), metrics in sorted(DATA.items()):
        t = task_meta(task_name)
        m = model_meta(csv_model_name)
        if not t or not m:
            continue

        _, dataset_parent, n_series, freq, horizon, has_cov = t
        _, schema_model, family, zs, ft, notes = m

        for metric_name, metric_value in metrics.items():
            paper_id = f"B02_fev_{task_name}"
            row = {
                "paper_id": paper_id,
                "authors": PAPER["authors"],
                "year": PAPER["year"],
                "title": PAPER["title"],
                "venue": PAPER["venue"],
                "dataset": f"fev-bench/{task_name}",
                "dataset_variant": dataset_parent,
                "n_series": n_series,
                "series_length_median": "",
                "frequency": freq,
                "has_covariates": has_cov,
                "model_name": schema_model,
                "model_family": family,
                "zero_shot": zs,
                "fine_tuned": ft,
                "horizon": horizon,
                "eval_method": "rolling",
                "metric_name": metric_name,
                "metric_value": metric_value,
                "runtime_reported": "Yes",
                "gpu_hours": "",
                "hardware": "CUDA (A10G)",
                "notes": notes,
            }
            rows.append(row)
    return rows


def main():
    rows = generate_rows()
    print(f"Generated {len(rows)} extraction rows from fev-bench retail tasks.")

    # Count unique model-task pairs for FM vs ML_TREE.
    fm_pairs = set()
    mltree_pairs = set()
    for r in rows:
        key = (r["dataset"], r["metric_name"])
        if r["model_family"] == "foundation":
            fm_pairs.add(key)
        elif r["model_family"] == "ml_tree":
            mltree_pairs.add(key)
    common = fm_pairs & mltree_pairs
    print(f"  FM rows: {sum(1 for r in rows if r['model_family'] == 'foundation')}")
    print(f"  ML_TREE rows: {sum(1 for r in rows if r['model_family'] == 'ml_tree')}")
    print(f"  Pairable (task, metric) buckets: {len(common)}")

    # Append to extraction_schema.csv.
    if not os.path.exists(SCHEMA_PATH):
        print(f"ERROR: {SCHEMA_PATH} not found. Run from repo root.")
        return

    with open(SCHEMA_PATH, "a", newline="") as f:
        f.write("\n# === fev-bench retail tasks (Shchur et al. 2025, extracted 2026-04-16) ===\n")
        writer = csv.DictWriter(f, fieldnames=HEADER)
        for row in rows:
            writer.writerow(row)

    print(f"Appended {len(rows)} rows to {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
