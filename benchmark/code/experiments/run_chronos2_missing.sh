#!/usr/bin/env bash
# =============================================================================
# chronos2 gap-fill: 6 missing / n=100 runs → n=3000.
#   M5:      h7, h14, h28  @ max_series=3000
#   Favorita: h7, h14, h28 @ max_series=3000
#
# Estimated: ~20-26h on M-series MacBook.
# Usage:
#   cd ~/Documents/Repos/large-scale-demand-forecasting-benchmark
#   nohup bash benchmark/code/experiments/run_chronos2_missing.sh \
#     > logs/chronos2_missing.log 2>&1 &
#   echo $!
# =============================================================================

set -euo pipefail

VENV="${FM_LOCAL_VENV:-$HOME/venvs/fm-local}"
PY="$VENV/bin/python"

if [[ ! -x "$PY" ]]; then
    echo "ERROR: venv not found at $VENV" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/benchmark/code:${PYTHONPATH:-}"

M5_SALES="${M5_SALES_PATH:-data/raw/m5/sales_train_validation.csv}"
M5_CAL="${M5_CALENDAR_PATH:-data/raw/m5/calendar.csv}"
M5_PRICES="${M5_PRICES_PATH:-data/raw/m5/sell_prices.csv}"

FAV_TRAIN="${FAVORITA_TRAIN_PATH:-data/raw/favorita/train.csv}"
FAV_OIL="${FAVORITA_OIL_PATH:-data/raw/favorita/oil.csv}"
FAV_HOLIDAYS="${FAVORITA_HOLIDAYS_PATH:-data/raw/favorita/holidays_events.csv}"
FAV_STORES="${FAVORITA_STORES_PATH:-data/raw/favorita/stores.csv}"
FAV_TX="${FAVORITA_TX_PATH:-data/raw/favorita/transactions.csv}"

for path in "$M5_SALES" "$M5_CAL" "$FAV_TRAIN"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: data not found: $path" >&2
        exit 1
    fi
done

HARDWARE="M_SERIES_MAC"
MAX_SERIES=3000
LOG_DIR="$REPO_ROOT/logs/chronos2_missing_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

DONE=0
FAILED=0
TOTAL=6

run_job() {
    local tag="$1"; shift
    DONE=$((DONE + 1))
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$DONE/$TOTAL] $tag"
    "$PY" benchmark/code/experiments/run_gap_filling.py "$@" \
        2>&1 | tee "$LOG_DIR/$tag.log" || {
        echo "FAIL: $tag — see $LOG_DIR/$tag.log" >&2
        FAILED=$((FAILED + 1))
    }
    echo ""
}

echo "=== chronos2 gap-fill (6 jobs, n=$MAX_SERIES) ==="
echo "Logs: $LOG_DIR"
echo ""

# M5: h28 first (fastest), then h14, h7
run_job "chronos2_m5_h28_n3000" \
    --model chronos2 --dataset m5 --horizon 28 \
    --hardware "$HARDWARE" --max-series "$MAX_SERIES" \
    --sales-path "$M5_SALES" --calendar-path "$M5_CAL" --prices-path "$M5_PRICES"

run_job "chronos2_m5_h14_n3000" \
    --model chronos2 --dataset m5 --horizon 14 \
    --hardware "$HARDWARE" --max-series "$MAX_SERIES" \
    --sales-path "$M5_SALES" --calendar-path "$M5_CAL" --prices-path "$M5_PRICES"

run_job "chronos2_m5_h7_n3000" \
    --model chronos2 --dataset m5 --horizon 7 \
    --hardware "$HARDWARE" --max-series "$MAX_SERIES" \
    --sales-path "$M5_SALES" --calendar-path "$M5_CAL" --prices-path "$M5_PRICES"

# Favorita: h28 first (fastest), then h14, h7
run_job "chronos2_favorita_h28_n3000" \
    --model chronos2 --dataset favorita --horizon 28 \
    --hardware "$HARDWARE" --max-series "$MAX_SERIES" \
    --sales-path "$FAV_TRAIN" --oil-path "$FAV_OIL" \
    --holidays-path "$FAV_HOLIDAYS" --stores-path "$FAV_STORES" \
    --transactions-path "$FAV_TX"

run_job "chronos2_favorita_h14_n3000" \
    --model chronos2 --dataset favorita --horizon 14 \
    --hardware "$HARDWARE" --max-series "$MAX_SERIES" \
    --sales-path "$FAV_TRAIN" --oil-path "$FAV_OIL" \
    --holidays-path "$FAV_HOLIDAYS" --stores-path "$FAV_STORES" \
    --transactions-path "$FAV_TX"

run_job "chronos2_favorita_h7_n3000" \
    --model chronos2 --dataset favorita --horizon 7 \
    --hardware "$HARDWARE" --max-series "$MAX_SERIES" \
    --sales-path "$FAV_TRAIN" --oil-path "$FAV_OIL" \
    --holidays-path "$FAV_HOLIDAYS" --stores-path "$FAV_STORES" \
    --transactions-path "$FAV_TX"

echo "=== Done: $TOTAL jobs, $FAILED failed ==="
echo "Finished: $(date)"
echo ""
echo "Next steps:"
echo "  python tools/export_mlflow_to_csv.py --out benchmark/results/local_fm_sweep.csv"
echo "  Rscript analysis/meta_regression.R"
