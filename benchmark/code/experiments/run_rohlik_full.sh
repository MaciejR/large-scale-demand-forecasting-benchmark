#!/usr/bin/env bash
# =============================================================================
# Rohlik full-series sweep: 5 FMs × 3 horizons, no sampling.
# ~5-15h on Apple M-series MacBook. Run overnight.
#
# Usage:
#   cd ~/Documents/Repos/large-scale-demand-forecasting-benchmark
#   bash benchmark/code/experiments/run_rohlik_full.sh
#
# After completion:
#   python tools/export_mlflow_to_csv.py --out benchmark/results/local_fm_sweep.csv
#   Rscript analysis/meta_regression.R
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

ROHLIK_TRAIN="${ROHLIK_TRAIN_PATH:-data/raw/rohlik-v2/sales_train.csv}"
ROHLIK_CAL="${ROHLIK_CALENDAR_PATH:-data/raw/rohlik-v2/calendar.csv}"

if [[ ! -f "$ROHLIK_TRAIN" ]]; then
    echo "ERROR: Rohlik data not found at $ROHLIK_TRAIN" >&2
    exit 1
fi

MODELS=(chronos_bolt_tiny tirex chronos2 moirai2 timesfm25)
HORIZONS=(7 14 28)
HARDWARE="M_SERIES_MAC"

LOG_DIR="$REPO_ROOT/logs/rohlik_full_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

TOTAL=0
FAILED=0

echo "=== Rohlik full-series sweep (5,390 series) ==="
echo "Models: ${MODELS[*]}"
echo "Horizons: ${HORIZONS[*]}"
echo "Logs: $LOG_DIR"
echo ""

for model in "${MODELS[@]}"; do
    for horizon in "${HORIZONS[@]}"; do
        TOTAL=$((TOTAL + 1))
        tag="${model}_rohlik_h${horizon}"
        log="$LOG_DIR/$tag.log"
        echo "[$(date +%H:%M:%S)] [$TOTAL/15] $tag"

        "$PY" benchmark/code/experiments/run_gap_filling.py \
            --model "$model" \
            --dataset rohlik \
            --horizon "$horizon" \
            --hardware "$HARDWARE" \
            --sales-path "$ROHLIK_TRAIN" \
            --calendar-path "$ROHLIK_CAL" \
            2>&1 | tee "$log" || {
                echo "FAIL: $tag — see $log" >&2
                FAILED=$((FAILED + 1))
            }
        echo ""
    done
done

echo "=== Done: $TOTAL jobs, $FAILED failed ==="
echo "Logs: $LOG_DIR"
echo ""
echo "Next:"
echo "  python tools/export_mlflow_to_csv.py --out benchmark/results/local_fm_sweep.csv"
echo "  Rscript analysis/meta_regression.R"
