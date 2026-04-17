#!/bin/bash
# Post-sweep integration: export TimesFM 2.5 MLflow runs → update CSV → rerun R.
#
# Run this after run_timesfm25_sweep.sh completes.
#
# Steps:
#   1. Export all MLflow runs (local) to local_fm_sweep.csv
#   2. Re-inject Azure baseline cost data (not in MLflow)
#   3. Regenerate extraction_schema.csv with fev-bench data
#   4. Rerun meta_regression.R to update all figures and tables
#
# Usage: bash tools/integrate_timesfm25.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON=~/venvs/fm-local/bin/python

echo "=== Step 1: Export MLflow runs ==="
$PYTHON tools/export_mlflow_to_csv.py \
  --out benchmark/results/local_fm_sweep.csv

echo "=== Step 2: Re-inject Azure baseline costs ==="
# The export_mlflow_to_csv.py wipes cost data for Azure baselines (they don't
# log cost_usd in MLflow). Re-inject from the paper's appendix tables.
$PYTHON -c "
import csv

costs = {
    ('M5', 'seasonal_naive', '7'): (236.9, 0.025),
    ('M5', 'seasonal_naive', '14'): (176.9, 0.019),
    ('M5', 'seasonal_naive', '28'): (139.6, 0.015),
    ('M5', 'lightgbm_cov', '7'): (300.3, 0.032),
    ('M5', 'lightgbm_cov', '14'): (301.1, 0.032),
    ('M5', 'lightgbm_cov', '28'): (284.3, 0.030),
    ('M5', 'lightgbm_direct', '7'): (1114.4, 0.118),
    ('M5', 'lightgbm_direct', '14'): (2003.2, 0.212),
    ('M5', 'lightgbm_direct', '28'): (3728.8, 0.394),
    ('Rohlik', 'seasonal_naive', '7'): (8.5, 0.0009),
    ('Rohlik', 'seasonal_naive', '14'): (6.9, 0.0007),
    ('Rohlik', 'seasonal_naive', '28'): (5.8, 0.0006),
    ('Rohlik', 'lightgbm_cov', '7'): (29.6, 0.0031),
    ('Rohlik', 'lightgbm_cov', '14'): (30.6, 0.0032),
    ('Rohlik', 'lightgbm_cov', '28'): (29.1, 0.0031),
    ('Rohlik', 'lightgbm_direct', '7'): (141.1, 0.0149),
    ('Rohlik', 'lightgbm_direct', '14'): (265.6, 0.0280),
    ('Rohlik', 'lightgbm_direct', '28'): (524.3, 0.0553),
    ('Favorita', 'seasonal_naive', '7'): (65.0, 0.0068),
    ('Favorita', 'seasonal_naive', '14'): (49.0, 0.0052),
    ('Favorita', 'seasonal_naive', '28'): (39.0, 0.0041),
    ('Favorita', 'lightgbm_cov', '7'): (236.0, 0.0249),
    ('Favorita', 'lightgbm_cov', '14'): (230.0, 0.0242),
    ('Favorita', 'lightgbm_cov', '28'): (230.0, 0.0243),
    ('Favorita', 'lightgbm_direct', '7'): (1015.0, 0.1071),
    ('Favorita', 'lightgbm_direct', '14'): (1907.0, 0.2012),
    ('Favorita', 'lightgbm_direct', '28'): (3588.0, 0.3787),
}

TDP_KW = 0.040
CO2_INTENSITY = 0.041
path = 'benchmark/results/local_fm_sweep.csv'

with open(path) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fields = reader.fieldnames

updated = 0
for row in rows:
    ds_key = row['dataset']
    if ds_key.lower() in ('rohlik_v2', 'rohlik v2'):
        ds_key = 'Rohlik'
    key = (ds_key, row['model_name'], str(row['horizon']))
    if key in costs:
        runtime, cost = costs[key]
        co2 = (runtime / 3600.0) * TDP_KW * CO2_INTENSITY
        row['runtime_sec'] = str(runtime)
        row['cost_usd'] = str(cost)
        row['co2_kg'] = str(round(co2, 8))
        updated += 1

with open(path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(f'Re-injected costs for {updated} baseline rows')
"

echo "=== Step 3: Regenerate extraction_schema.csv ==="
$PYTHON analysis/extract_fev_bench_retail.py

echo "=== Step 4: Rerun meta-regression ==="
Rscript analysis/meta_regression.R

echo "=== Step 5: Verify ==="
echo "Check analysis/figures/table_6_1_primary_intercept.txt for updated k and delta."
cat analysis/figures/table_6_1_primary_intercept.txt

echo ""
echo "=== Integration complete ==="
echo "Next: update paper numbers if delta changed, then recompile LaTeX."
