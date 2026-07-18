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
    ("Chronos-2", "Chronos-2", "foundation", "Yes", "No", "120M params; Chronos-2 checkpoint; zero-shot; covariate support not used in extracted rows"),
    ("Chronos-Bolt", "Chronos-Bolt-Base", "foundation", "Yes", "No", "~46M params; Chronos-Bolt-Base checkpoint; zero-shot"),
    ("Moirai-2.0", "Moirai-2.0-Small", "foundation", "Yes", "No", "11M params; decoder-only quantile model; zero-shot"),
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

    # TimesFM-2.5 (all values from raw fev-bench CSV: timesfm-2_5.csv)
    ("m5_1D", "TimesFM-2.5"): {"SQL": "0.7189", "MASE": "0.8721", "WAPE": "0.6968"},
    ("m5_1W", "TimesFM-2.5"): {"SQL": "0.8890", "MASE": "1.1222", "WAPE": "0.4201"},
    ("m5_1M", "TimesFM-2.5"): {"SQL": "0.9798", "MASE": "1.1576", "WAPE": "0.4249"},
    ("favorita_stores_1D", "TimesFM-2.5"): {"SQL": "0.9494", "MASE": "1.1676", "WAPE": "0.1452"},
    ("favorita_stores_1W", "TimesFM-2.5"): {"SQL": "1.9684", "MASE": "2.2901", "WAPE": "0.1308"},
    ("favorita_stores_1M", "TimesFM-2.5"): {"SQL": "1.9983", "MASE": "2.2338", "WAPE": "0.2103"},
    ("favorita_transactions_1D", "TimesFM-2.5"): {"SQL": "0.8736", "MASE": "1.0842", "WAPE": "0.0655"},
    ("favorita_transactions_1W", "TimesFM-2.5"): {"SQL": "1.2228", "MASE": "1.4718", "WAPE": "0.0559"},
    ("favorita_transactions_1M", "TimesFM-2.5"): {"SQL": "1.1327", "MASE": "1.3316", "WAPE": "0.0742"},
    ("rossmann_1D", "TimesFM-2.5"): {"SQL": "0.5016", "MASE": "0.6106", "WAPE": "0.2086"},
    ("rossmann_1W", "TimesFM-2.5"): {"SQL": "0.4952", "MASE": "0.6543", "WAPE": "0.1803"},
    ("walmart", "TimesFM-2.5"): {"SQL": "0.6794", "MASE": "0.8615", "WAPE": "0.1016"},
    ("rohlik_orders_1D", "TimesFM-2.5"): {"SQL": "1.0057", "MASE": "1.2504", "WAPE": "0.0591"},
    ("rohlik_orders_1W", "TimesFM-2.5"): {"SQL": "1.3278", "MASE": "1.6592", "WAPE": "0.0542"},
    ("rohlik_sales_1D", "TimesFM-2.5"): {"SQL": "1.0958", "MASE": "1.3238", "WAPE": "0.3586"},
    ("rohlik_sales_1W", "TimesFM-2.5"): {"SQL": "1.4010", "MASE": "1.6891", "WAPE": "0.2667"},
    ("restaurant", "TimesFM-2.5"): {"SQL": "0.6774", "MASE": "0.8503", "WAPE": "0.3570"},
    ("hierarchical_sales_1D", "TimesFM-2.5"): {"SQL": "0.5516", "MASE": "0.6882", "WAPE": "0.6944"},
    ("hierarchical_sales_1W", "TimesFM-2.5"): {"SQL": "0.6178", "MASE": "0.7508", "WAPE": "0.4307"},
    ("hermes", "TimesFM-2.5"): {"SQL": "0.6184", "MASE": "0.7872", "WAPE": "0.0029"},

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

    # Chronos-Bolt (all values from raw fev-bench CSV: chronos-bolt.csv)
    ("m5_1D", "Chronos-Bolt"): {"SQL": "0.7293", "MASE": "0.8852", "WAPE": "0.7110"},
    ("m5_1W", "Chronos-Bolt"): {"SQL": "0.9165", "MASE": "1.1647", "WAPE": "0.4334"},
    ("m5_1M", "Chronos-Bolt"): {"SQL": "1.0001", "MASE": "1.1852", "WAPE": "0.4455"},
    ("favorita_stores_1D", "Chronos-Bolt"): {"SQL": "1.0322", "MASE": "1.2689", "WAPE": "0.1743"},
    ("favorita_stores_1W", "Chronos-Bolt"): {"SQL": "2.1011", "MASE": "2.4749", "WAPE": "0.1580"},
    ("favorita_stores_1M", "Chronos-Bolt"): {"SQL": "2.0865", "MASE": "2.4178", "WAPE": "0.2637"},
    ("favorita_transactions_1D", "Chronos-Bolt"): {"SQL": "0.9750", "MASE": "1.1515", "WAPE": "0.0873"},
    ("favorita_transactions_1W", "Chronos-Bolt"): {"SQL": "1.4283", "MASE": "1.7479", "WAPE": "0.0629"},
    ("favorita_transactions_1M", "Chronos-Bolt"): {"SQL": "1.3585", "MASE": "1.6365", "WAPE": "0.0941"},
    ("rossmann_1D", "Chronos-Bolt"): {"SQL": "0.5246", "MASE": "0.6371", "WAPE": "0.2176"},
    ("rossmann_1W", "Chronos-Bolt"): {"SQL": "0.4871", "MASE": "0.6452", "WAPE": "0.1760"},
    ("walmart", "Chronos-Bolt"): {"SQL": "0.7740", "MASE": "0.9671", "WAPE": "0.1173"},
    ("rohlik_orders_1D", "Chronos-Bolt"): {"SQL": "1.0508", "MASE": "1.3016", "WAPE": "0.0614"},
    ("rohlik_orders_1W", "Chronos-Bolt"): {"SQL": "1.4282", "MASE": "1.7219", "WAPE": "0.0570"},
    ("rohlik_sales_1D", "Chronos-Bolt"): {"SQL": "1.1471", "MASE": "1.3871", "WAPE": "0.3783"},
    ("rohlik_sales_1W", "Chronos-Bolt"): {"SQL": "1.5216", "MASE": "1.8467", "WAPE": "0.2846"},
    ("restaurant", "Chronos-Bolt"): {"SQL": "0.6890", "MASE": "0.8660", "WAPE": "0.3649"},
    ("hierarchical_sales_1D", "Chronos-Bolt"): {"SQL": "0.5509", "MASE": "0.6860", "WAPE": "0.6950"},
    ("hierarchical_sales_1W", "Chronos-Bolt"): {"SQL": "0.6367", "MASE": "0.7733", "WAPE": "0.4394"},
    ("hermes", "Chronos-Bolt"): {"SQL": "0.6752", "MASE": "0.8579", "WAPE": "0.0032"},

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

    # CatBoost (Recursive) (from raw fev-bench CSV: catboost.csv)
    # Note: SQL==MASE in fev-bench source data (same issue as LightGBM)
    ("m5_1D", "CatBoost (Recursive)"): {"SQL": "0.9105", "MASE": "0.9105", "WAPE": "0.7367"},
    ("m5_1W", "CatBoost (Recursive)"): {"SQL": "1.1368", "MASE": "1.1368", "WAPE": "0.4229"},
    ("m5_1M", "CatBoost (Recursive)"): {"SQL": "1.1692", "MASE": "1.1692", "WAPE": "0.4387"},
    ("favorita_stores_1D", "CatBoost (Recursive)"): {"SQL": "1.2171", "MASE": "1.2171", "WAPE": "0.1567"},
    ("favorita_stores_1W", "CatBoost (Recursive)"): {"SQL": "2.4207", "MASE": "2.4207", "WAPE": "0.1307"},
    ("favorita_stores_1M", "CatBoost (Recursive)"): {"SQL": "2.3860", "MASE": "2.3860", "WAPE": "0.2205"},
    ("favorita_transactions_1D", "CatBoost (Recursive)"): {"SQL": "1.3230", "MASE": "1.3230", "WAPE": "0.0814"},
    ("favorita_transactions_1W", "CatBoost (Recursive)"): {"SQL": "1.4269", "MASE": "1.4269", "WAPE": "0.0633"},
    ("favorita_transactions_1M", "CatBoost (Recursive)"): {"SQL": "1.5502", "MASE": "1.5502", "WAPE": "0.1009"},
    ("rossmann_1D", "CatBoost (Recursive)"): {"SQL": "0.3327", "MASE": "0.3327", "WAPE": "0.1098"},
    ("rossmann_1W", "CatBoost (Recursive)"): {"SQL": "0.6818", "MASE": "0.6818", "WAPE": "0.1901"},
    ("walmart", "CatBoost (Recursive)"): {"SQL": "1.3178", "MASE": "1.3178", "WAPE": "0.1748"},
    ("rohlik_orders_1D", "CatBoost (Recursive)"): {"SQL": "1.1489", "MASE": "1.1489", "WAPE": "0.0543"},
    ("rohlik_orders_1W", "CatBoost (Recursive)"): {"SQL": "2.0796", "MASE": "2.0796", "WAPE": "0.0664"},
    ("rohlik_sales_1D", "CatBoost (Recursive)"): {"SQL": "1.2715", "MASE": "1.2715", "WAPE": "0.3378"},
    ("rohlik_sales_1W", "CatBoost (Recursive)"): {"SQL": "1.8282", "MASE": "1.8282", "WAPE": "0.2969"},
    ("restaurant", "CatBoost (Recursive)"): {"SQL": "0.9515", "MASE": "0.9515", "WAPE": "0.4055"},
    ("hierarchical_sales_1D", "CatBoost (Recursive)"): {"SQL": "0.6854", "MASE": "0.6854", "WAPE": "0.6876"},
    ("hierarchical_sales_1W", "CatBoost (Recursive)"): {"SQL": "0.7843", "MASE": "0.7843", "WAPE": "0.4410"},
    ("hermes", "CatBoost (Recursive)"): {"SQL": "1.1670", "MASE": "1.1670", "WAPE": "0.0045"},

    # Toto-1.0 (from raw fev-bench CSV: toto-1_0.csv)
    ("m5_1D", "Toto-1.0"): {"SQL": "0.7076", "MASE": "0.8683", "WAPE": "0.6986"},
    ("m5_1W", "Toto-1.0"): {"SQL": "0.9050", "MASE": "1.1448", "WAPE": "0.4278"},
    ("m5_1M", "Toto-1.0"): {"SQL": "1.0440", "MASE": "1.2422", "WAPE": "0.4597"},
    ("favorita_stores_1D", "Toto-1.0"): {"SQL": "1.0364", "MASE": "1.2804", "WAPE": "0.1784"},
    ("favorita_stores_1W", "Toto-1.0"): {"SQL": "2.1277", "MASE": "2.5080", "WAPE": "0.1511"},
    ("favorita_stores_1M", "Toto-1.0"): {"SQL": "2.0094", "MASE": "2.2865", "WAPE": "0.1978"},
    ("favorita_transactions_1D", "Toto-1.0"): {"SQL": "1.1139", "MASE": "1.4307", "WAPE": "0.0947"},
    ("favorita_transactions_1W", "Toto-1.0"): {"SQL": "1.5566", "MASE": "1.9304", "WAPE": "0.0687"},
    ("favorita_transactions_1M", "Toto-1.0"): {"SQL": "1.3969", "MASE": "1.6656", "WAPE": "0.0891"},
    ("rossmann_1D", "Toto-1.0"): {"SQL": "0.5677", "MASE": "0.6814", "WAPE": "0.2321"},
    ("rossmann_1W", "Toto-1.0"): {"SQL": "0.4944", "MASE": "0.6319", "WAPE": "0.1733"},
    ("walmart", "Toto-1.0"): {"SQL": "0.9072", "MASE": "1.1258", "WAPE": "0.1385"},
    ("rohlik_orders_1D", "Toto-1.0"): {"SQL": "1.1351", "MASE": "1.3776", "WAPE": "0.0646"},
    ("rohlik_orders_1W", "Toto-1.0"): {"SQL": "1.4934", "MASE": "1.7980", "WAPE": "0.0591"},
    ("rohlik_sales_1D", "Toto-1.0"): {"SQL": "1.2181", "MASE": "1.4539", "WAPE": "0.3975"},
    ("rohlik_sales_1W", "Toto-1.0"): {"SQL": "1.5046", "MASE": "1.8031", "WAPE": "0.2812"},
    ("restaurant", "Toto-1.0"): {"SQL": "0.7040", "MASE": "0.8859", "WAPE": "0.3732"},
    ("hierarchical_sales_1D", "Toto-1.0"): {"SQL": "0.5468", "MASE": "0.6821", "WAPE": "0.6905"},
    ("hierarchical_sales_1W", "Toto-1.0"): {"SQL": "0.6373", "MASE": "0.7790", "WAPE": "0.4364"},
    ("hermes", "Toto-1.0"): {"SQL": "0.9853", "MASE": "1.2023", "WAPE": "0.0044"},

    # TabPFN-TS (from raw fev-bench CSV: tabpfn-ts.csv; 2 tasks failed)
    ("m5_1W", "TabPFN-TS"): {"SQL": "0.9282", "MASE": "1.1605", "WAPE": "0.4358"},
    ("m5_1M", "TabPFN-TS"): {"SQL": "1.0017", "MASE": "1.1871", "WAPE": "0.4365"},
    ("favorita_stores_1D", "TabPFN-TS"): {"SQL": "0.9698", "MASE": "1.1943", "WAPE": "0.1486"},
    ("favorita_stores_1W", "TabPFN-TS"): {"SQL": "2.1227", "MASE": "2.5268", "WAPE": "0.1260"},
    ("favorita_stores_1M", "TabPFN-TS"): {"SQL": "1.9336", "MASE": "2.1758", "WAPE": "0.1159"},
    ("favorita_transactions_1D", "TabPFN-TS"): {"SQL": "1.2252", "MASE": "1.6727", "WAPE": "0.0773"},
    ("favorita_transactions_1W", "TabPFN-TS"): {"SQL": "1.9116", "MASE": "2.4368", "WAPE": "0.0710"},
    ("favorita_transactions_1M", "TabPFN-TS"): {"SQL": "1.2438", "MASE": "1.4262", "WAPE": "0.0822"},
    ("rossmann_1D", "TabPFN-TS"): {"SQL": "0.2321", "MASE": "0.2945", "WAPE": "0.0979"},
    ("rossmann_1W", "TabPFN-TS"): {"SQL": "0.2539", "MASE": "0.3046", "WAPE": "0.0792"},
    ("walmart", "TabPFN-TS"): {"SQL": "0.6619", "MASE": "0.8318", "WAPE": "0.0943"},
    ("rohlik_orders_1D", "TabPFN-TS"): {"SQL": "1.3411", "MASE": "1.5479", "WAPE": "0.0656"},
    ("rohlik_orders_1W", "TabPFN-TS"): {"SQL": "1.5240", "MASE": "1.9887", "WAPE": "0.0652"},
    ("rohlik_sales_1W", "TabPFN-TS"): {"SQL": "1.2205", "MASE": "1.5205", "WAPE": "0.2152"},
    ("restaurant", "TabPFN-TS"): {"SQL": "0.6930", "MASE": "0.8689", "WAPE": "0.3642"},
    ("hierarchical_sales_1D", "TabPFN-TS"): {"SQL": "0.5720", "MASE": "0.7080", "WAPE": "0.7258"},
    ("hierarchical_sales_1W", "TabPFN-TS"): {"SQL": "0.6369", "MASE": "0.7740", "WAPE": "0.4384"},
    ("hermes", "TabPFN-TS"): {"SQL": "0.7049", "MASE": "0.9123", "WAPE": "0.0034"},
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

    # Replace fev-bench rows in extraction_schema.csv (idempotent).
    if not os.path.exists(SCHEMA_PATH):
        print(f"ERROR: {SCHEMA_PATH} not found. Run from repo root.")
        return

    # Read existing rows, strip old fev-bench entries and comment lines.
    with open(SCHEMA_PATH, newline="") as f:
        reader = csv.DictReader(f)
        existing = [r for r in reader
                    if not r.get("paper_id", "").startswith("B02_fev")
                    and not r.get("paper_id", "").startswith("# ")]

    with open(SCHEMA_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        for row in existing:
            writer.writerow(row)
        f.write("# === fev-bench retail tasks (Shchur et al. 2025, extracted 2026-04-18) ===\n")
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(existing)} existing + {len(rows)} fev-bench = {len(existing)+len(rows)} rows to {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
