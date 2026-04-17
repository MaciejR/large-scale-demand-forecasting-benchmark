#!/bin/bash
# TimesFM 2.5 gap-filling sweep: 3 datasets × 3 horizons = 9 cells.
# Uses n=100 series per cell (consistent with existing Source B FM runs).
#
# Usage: bash benchmark/code/experiments/run_timesfm25_sweep.sh
# Requires: ~/venvs/fm-local with timesfm[torch] installed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

PYTHON=~/venvs/fm-local/bin/python
RUNNER="benchmark/code/experiments/run_gap_filling.py"
export PYTHONPATH="$REPO_ROOT/benchmark/code"

HARDWARE="M_SERIES_MAC"
MAX_SERIES=100

# --- M5 ---
M5_SALES="data/raw/m5/sales_train_validation.csv"
M5_CAL="data/raw/m5/calendar.csv"

for H in 7 14 28; do
  echo "=== TimesFM 2.5 — M5, h=$H ==="
  $PYTHON "$RUNNER" \
    --model timesfm25 \
    --dataset m5 \
    --horizon "$H" \
    --max-series "$MAX_SERIES" \
    --hardware "$HARDWARE" \
    --sales-path "$M5_SALES" \
    --calendar-path "$M5_CAL"
done

# --- Rohlik ---
ROHLIK_SALES="data/raw/rohlik-v2/sales_train.csv"
ROHLIK_CAL="data/raw/rohlik-v2/calendar.csv"

for H in 7 14 28; do
  echo "=== TimesFM 2.5 — Rohlik, h=$H ==="
  $PYTHON "$RUNNER" \
    --model timesfm25 \
    --dataset rohlik \
    --horizon "$H" \
    --max-series "$MAX_SERIES" \
    --hardware "$HARDWARE" \
    --sales-path "$ROHLIK_SALES" \
    --calendar-path "$ROHLIK_CAL"
done

# --- Favorita ---
FAVORITA_SALES="data/raw/favorita/train.csv"
export FAVORITA_TRAIN_PATH="$FAVORITA_SALES"

for H in 7 14 28; do
  echo "=== TimesFM 2.5 — Favorita, h=$H ==="
  $PYTHON "$RUNNER" \
    --model timesfm25 \
    --dataset favorita \
    --horizon "$H" \
    --max-series "$MAX_SERIES" \
    --hardware "$HARDWARE" \
    --sales-path "$FAVORITA_SALES"
done

echo "=== TimesFM 2.5 sweep complete ==="
