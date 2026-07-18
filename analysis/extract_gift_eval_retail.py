#!/usr/bin/env python3
"""
Extract GIFT-Eval retail (Sales domain) results into extraction_schema.csv rows.

Source: Aksu et al. (2024), "GIFT-Eval: A Benchmark for General Time Series
Forecasting Model Evaluation", NeurIPS 2024 TSALM Workshop.
Raw per-model CSVs from:
https://github.com/SalesforceAIResearch/gift-eval/tree/main/results/

GIFT-Eval reports 98 dataset configurations across 7 domains. We extract only
the "Sales" domain: car_parts, hierarchical_sales, restaurant (4 configs).

Metrics mapped:
  - MASE:  eval_metrics/MASE[0.5]
  - WAPE:  eval_metrics/ND[0.5]  (Normalized Deviation ≈ WAPE)
  - SQL:   eval_metrics/mean_weighted_sum_quantile_loss

Usage: python3 analysis/extract_gift_eval_retail.py
"""

import csv
import os

# ── Task metadata ──────────────────────────────────────────────────────
# (task_name, dataset_parent, n_series, frequency, horizon, has_covariates)
# n_series from GIFT-Eval dataset descriptions; horizons estimated from
# the "short" prediction-length category per frequency.
TASKS = [
    ("car_parts_M", "Car Parts", "2674", "M", "12", "No"),
    ("hierarchical_sales_D", "Hierarchical Sales", "118", "D", "14", "No"),
    ("hierarchical_sales_W", "Hierarchical Sales", "118", "W", "13", "No"),
    ("restaurant_D", "Restaurant", "813", "D", "14", "No"),
]

# Map task_name to GIFT-Eval dataset string for data lookup.
TASK_TO_GIFT = {
    "car_parts_M": "car_parts/M/short",
    "hierarchical_sales_D": "hierarchical_sales/D/short",
    "hierarchical_sales_W": "hierarchical_sales/W/short",
    "restaurant_D": "restaurant/D/short",
}

# ── Model metadata ─────────────────────────────────────────────────────
# (gift_model_name, schema_model_name, model_family, zero_shot, fine_tuned, notes)
MODELS = [
    ("Chronos-2", "Chronos-2", "foundation", "Yes", "No",
     "120M params; Chronos-2 checkpoint; zero-shot; univariate in GIFT-Eval"),
    ("TiRex", "TiRex", "foundation", "Yes", "No",
     "~35M params; xLSTM; zero-shot"),
    ("TimesFM-2.5", "TimesFM-2.5", "foundation", "Yes", "No",
     "200M params; decoder-only; zero-shot"),
    ("Moirai2", "Moirai-2.0-Small", "foundation", "Yes", "No",
     "11M params; decoder-only quantile model; zero-shot"),
    ("chronos_bolt_base", "Chronos-Bolt-Base", "foundation", "Yes", "No",
     "~46M params; Chronos-Bolt-Base checkpoint; zero-shot"),
    ("Toto_Open_Base_1.0", "Toto-1.0", "foundation", "Yes", "No",
     "foundation model; open base; zero-shot"),
    ("TabPFN-TS", "TabPFN-TS", "foundation", "Yes", "No",
     "~12M params; tabular PFN + temporal; zero-shot"),
    ("Auto_ETS", "Auto ETS", "statistical", "No", "Yes",
     "statsforecast Auto ETS; per-series fitted"),
    ("Seasonal_Naive", "Seasonal Naive", "statistical", "No", "Yes",
     "seasonal naive baseline"),
]

# ── Per-task per-model metric values ───────────────────────────────────
# Extracted from raw GitHub CSVs 2026-04-16.
# Format: {(gift_dataset_str, gift_model_name): {metric: value}}
# Metrics: MASE = eval_metrics/MASE[0.5], WAPE = eval_metrics/ND[0.5],
#          SQL = eval_metrics/mean_weighted_sum_quantile_loss
DATA = {
    # ── Chronos-2 ──
    ("car_parts/M/short", "Chronos-2"):
        {"MASE": "0.8360", "WAPE": "1.0871", "SQL": "0.9660"},
    ("hierarchical_sales/D/short", "Chronos-2"):
        {"MASE": "0.7440", "WAPE": "0.7091", "SQL": "0.5789"},
    ("hierarchical_sales/W/short", "Chronos-2"):
        {"MASE": "0.7093", "WAPE": "0.4039", "SQL": "0.3407"},
    ("restaurant/D/short", "Chronos-2"):
        {"MASE": "0.6777", "WAPE": "0.3252", "SQL": "0.2543"},

    # ── TiRex ──
    ("car_parts/M/short", "TiRex"):
        {"MASE": "0.8469", "WAPE": "1.1020", "SQL": "0.9952"},
    ("hierarchical_sales/D/short", "TiRex"):
        {"MASE": "0.7452", "WAPE": "0.7083", "SQL": "0.5702"},
    ("hierarchical_sales/W/short", "TiRex"):
        {"MASE": "0.7220", "WAPE": "0.4093", "SQL": "0.3477"},
    ("restaurant/D/short", "TiRex"):
        {"MASE": "0.6779", "WAPE": "0.3254", "SQL": "0.2548"},

    # ── TimesFM-2.5 ──
    ("car_parts/M/short", "TimesFM-2.5"):
        {"MASE": "0.8384", "WAPE": "1.1121", "SQL": "0.9421"},
    ("hierarchical_sales/D/short", "TimesFM-2.5"):
        {"MASE": "0.7450", "WAPE": "0.7087", "SQL": "0.5736"},
    ("hierarchical_sales/W/short", "TimesFM-2.5"):
        {"MASE": "0.7191", "WAPE": "0.4139", "SQL": "0.3478"},
    ("restaurant/D/short", "TimesFM-2.5"):
        {"MASE": "0.6818", "WAPE": "0.3274", "SQL": "0.2565"},

    # ── Moirai2 ──
    ("car_parts/M/short", "Moirai2"):
        {"MASE": "0.8266", "WAPE": "1.0844", "SQL": "0.9362"},
    ("hierarchical_sales/D/short", "Moirai2"):
        {"MASE": "0.7480", "WAPE": "0.7112", "SQL": "0.5770"},
    ("hierarchical_sales/W/short", "Moirai2"):
        {"MASE": "0.7381", "WAPE": "0.4199", "SQL": "0.3521"},
    ("restaurant/D/short", "Moirai2"):
        {"MASE": "0.6960", "WAPE": "0.3323", "SQL": "0.2604"},

    # ── Chronos-Bolt-Base ──
    ("car_parts/M/short", "chronos_bolt_base"):
        {"MASE": "0.8551", "WAPE": "1.1508", "SQL": "0.9945"},
    ("hierarchical_sales/D/short", "chronos_bolt_base"):
        {"MASE": "0.7428", "WAPE": "0.7080", "SQL": "0.5761"},
    ("hierarchical_sales/W/short", "chronos_bolt_base"):
        {"MASE": "0.7327", "WAPE": "0.4171", "SQL": "0.3526"},
    ("restaurant/D/short", "chronos_bolt_base"):
        {"MASE": "0.7004", "WAPE": "0.3373", "SQL": "0.2640"},

    # ── Toto-1.0 ──
    ("car_parts/M/short", "Toto_Open_Base_1.0"):
        {"MASE": "0.8104", "WAPE": "1.0198", "SQL": "0.8990"},
    ("hierarchical_sales/D/short", "Toto_Open_Base_1.0"):
        {"MASE": "0.7354", "WAPE": "0.7031", "SQL": "0.5704"},
    ("hierarchical_sales/W/short", "Toto_Open_Base_1.0"):
        {"MASE": "0.7443", "WAPE": "0.4198", "SQL": "0.3558"},
    ("restaurant/D/short", "Toto_Open_Base_1.0"):
        {"MASE": "0.7835", "WAPE": "0.3782", "SQL": "0.2974"},

    # ── TabPFN-TS ──
    ("car_parts/M/short", "TabPFN-TS"):
        {"MASE": "0.8476", "WAPE": "1.1239", "SQL": "0.9696"},
    ("hierarchical_sales/D/short", "TabPFN-TS"):
        {"MASE": "0.7595", "WAPE": "0.7274", "SQL": "0.5917"},
    ("hierarchical_sales/W/short", "TabPFN-TS"):
        {"MASE": "0.7311", "WAPE": "0.4130", "SQL": "0.3455"},
    ("restaurant/D/short", "TabPFN-TS"):
        {"MASE": "0.6978", "WAPE": "0.3350", "SQL": "0.2629"},

    # ── Auto ETS (statistical baseline) ──
    ("car_parts/M/short", "Auto_ETS"):
        {"MASE": "1.2200", "WAPE": "1.6000", "SQL": "1.3400"},
    ("hierarchical_sales/D/short", "Auto_ETS"):
        {"MASE": "0.9080", "WAPE": "0.8580", "SQL": "0.9310"},
    ("hierarchical_sales/W/short", "Auto_ETS"):
        {"MASE": "0.9160", "WAPE": "0.5890", "SQL": "0.6420"},
    ("restaurant/D/short", "Auto_ETS"):
        {"MASE": "0.8610", "WAPE": "0.4310", "SQL": "--"},
    # Note: restaurant Auto_ETS SQL=110.0 — anomalous, excluded.

    # ── Seasonal Naive (statistical baseline) ──
    ("car_parts/M/short", "Seasonal_Naive"):
        {"MASE": "1.2015", "WAPE": "1.6000", "SQL": "1.7217"},
    ("hierarchical_sales/D/short", "Seasonal_Naive"):
        {"MASE": "1.1348", "WAPE": "1.0583", "SQL": "1.7365"},
    ("hierarchical_sales/W/short", "Seasonal_Naive"):
        {"MASE": "1.0250", "WAPE": "0.6230", "SQL": "0.8322"},
    ("restaurant/D/short", "Seasonal_Naive"):
        {"MASE": "1.0061", "WAPE": "0.4907", "SQL": "0.6770"},
}

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "extraction_schema.csv")

HEADER = [
    "paper_id", "authors", "year", "title", "venue",
    "dataset", "dataset_variant", "n_series", "series_length_median",
    "frequency", "has_covariates", "model_name", "model_family",
    "zero_shot", "fine_tuned", "horizon", "eval_method",
    "metric_name", "metric_value", "runtime_reported", "gpu_hours",
    "hardware", "notes",
]


def generate_rows():
    rows = []
    for task_name, ds_parent, n_series, freq, horizon, has_cov in TASKS:
        gift_key = TASK_TO_GIFT[task_name]
        paper_id = f"B03_gift_{task_name}"

        for gift_model, schema_model, family, zs, ft, notes in MODELS:
            data_key = (gift_key, gift_model)
            if data_key not in DATA:
                continue
            metrics = DATA[data_key]

            for metric_name in ["MASE", "WAPE", "SQL"]:
                metric_value = metrics.get(metric_name, "--")
                if metric_value == "--":
                    continue
                row = {
                    "paper_id": paper_id,
                    "authors": "Aksu et al.",
                    "year": "2024",
                    "title": "GIFT-Eval: A Benchmark for General Time Series Forecasting Model Evaluation",
                    "venue": "NeurIPS TSALM Workshop",
                    "dataset": f"GIFT-Eval / {ds_parent} ({freq})",
                    "dataset_variant": gift_key,
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
                    "runtime_reported": "No",
                    "gpu_hours": "",
                    "hardware": "CUDA (GIFT-Eval leaderboard)",
                    "notes": notes,
                }
                rows.append(row)
    return rows


def main():
    rows = generate_rows()
    print(f"Generated {len(rows)} extraction rows from GIFT-Eval retail (Sales domain).")

    # Count FM vs baseline pairs.
    fm_pairs = set()
    stat_pairs = set()
    for r in rows:
        key = (r["dataset"], r["metric_name"])
        if r["model_family"] == "foundation":
            fm_pairs.add(key)
        elif r["model_family"] == "statistical":
            stat_pairs.add(key)
    common = fm_pairs & stat_pairs
    print(f"  FM rows: {sum(1 for r in rows if r['model_family'] == 'foundation')}")
    print(f"  Statistical rows: {sum(1 for r in rows if r['model_family'] == 'statistical')}")
    print(f"  Pairable (task, metric) buckets: {len(common)}")

    # Idempotent write: read existing rows, strip old B03_gift rows and
    # comment lines, then rewrite with new GIFT-Eval rows at the end.
    if not os.path.exists(SCHEMA_PATH):
        print(f"ERROR: {SCHEMA_PATH} not found. Run from repo root.")
        return

    with open(SCHEMA_PATH, newline="") as f:
        reader = csv.DictReader(f)
        existing = [r for r in reader
                    if not r.get("paper_id", "").startswith("B03_gift")
                    and not r.get("paper_id", "").startswith("# ")]

    with open(SCHEMA_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        for r in existing:
            writer.writerow(r)
        for row in rows:
            writer.writerow(row)

    total = len(existing) + len(rows)
    print(f"Wrote {total} rows to {SCHEMA_PATH} ({len(existing)} existing + {len(rows)} GIFT-Eval)")


if __name__ == "__main__":
    main()
