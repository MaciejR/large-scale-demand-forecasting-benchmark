#!/usr/bin/env bash
# Run Chronos-2 and Moirai-2 on all 3 datasets × 3 horizons (100 series each).
# Matches original Source B sample size for consistency.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
PY="${FM_LOCAL_VENV:-$HOME/venvs/fm-local}/bin/python"
export PYTHONPATH="$REPO/benchmark/code:${PYTHONPATH:-}"

# Data paths
export M5_SALES_PATH="$REPO/data/raw/m5/sales_train_validation.csv"
export M5_CALENDAR_PATH="$REPO/data/raw/m5/calendar.csv"
export FAVORITA_TRAIN_PATH="$REPO/data/raw/favorita/train.csv"
export ROHLIK_TRAIN_PATH="$REPO/data/raw/rohlik-v2/sales_train.csv"
export ROHLIK_CALENDAR_PATH="$REPO/data/raw/rohlik-v2/calendar.csv"

RUNNER="$REPO/benchmark/code/experiments/run_gap_filling.py"
MAX_SERIES=100
HW="M_SERIES_MAC"

LOG_DIR="$REPO/logs/new_fms_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

run_one() {
    local model="$1" dataset="$2" horizon="$3"
    local tag="${model}_${dataset}_h${horizon}"
    local log="$LOG_DIR/$tag.log"
    echo "[$(date +%H:%M:%S)] Running $tag..."

    local -a args=(--model "$model" --dataset "$dataset" --horizon "$horizon" --hardware "$HW" --max-series "$MAX_SERIES")
    case "$dataset" in
        rohlik)   args+=(--sales-path "$ROHLIK_TRAIN_PATH" --calendar-path "$ROHLIK_CALENDAR_PATH") ;;
        favorita) args+=(--sales-path "$FAVORITA_TRAIN_PATH") ;;
        m5)       args+=(--sales-path "$M5_SALES_PATH" --calendar-path "$M5_CALENDAR_PATH") ;;
    esac

    if "$PY" "$RUNNER" "${args[@]}" 2>&1 | tee "$log"; then
        echo "[$(date +%H:%M:%S)] $tag OK"
    else
        echo "[$(date +%H:%M:%S)] $tag FAILED" >&2
    fi
    echo ""
}

echo "=== New FM sweep: Chronos-2 + Moirai-2 ==="
echo "Max series: $MAX_SERIES, Hardware: $HW"
echo "Logs: $LOG_DIR"
echo ""

for model in chronos2 moirai2; do
    for dataset in rohlik favorita m5; do
        for horizon in 7 14 28; do
            run_one "$model" "$dataset" "$horizon"
        done
    done
done

echo "=== All done ==="
