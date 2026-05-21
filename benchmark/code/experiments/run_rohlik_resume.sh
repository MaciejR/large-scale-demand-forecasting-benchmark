#!/usr/bin/env bash
# =============================================================================
# Rohlik full-series RESUME: 4 remaining FMs × 3 horizons.
# Chronos-Bolt-Tiny already completed full-series in the first sweep.
#
# Order: fastest first (moirai2 ~2h, chronos2 ~8h, tirex ~12h, timesfm25 ~50h)
# TiRex forced to CPU (MPS xLSTM fallback hangs on full series).
#
# Estimated total: ~3 days on M-series MacBook. Run with nohup:
#   cd ~/Documents/Repos/large-scale-demand-forecasting-benchmark
#   nohup bash benchmark/code/experiments/run_rohlik_resume.sh > rohlik_resume.log 2>&1 &
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

# Force TiRex to CPU — MPS xLSTM fallback dispatches one element at a time
# through MPSGraph and stalls on >100 series. CPU path is 5-10x faster.
export TIREX_FORCE_CPU=1

ROHLIK_TRAIN="${ROHLIK_TRAIN_PATH:-data/raw/rohlik-v2/sales_train.csv}"
ROHLIK_CAL="${ROHLIK_CALENDAR_PATH:-data/raw/rohlik-v2/calendar.csv}"

if [[ ! -f "$ROHLIK_TRAIN" ]]; then
    echo "ERROR: Rohlik data not found at $ROHLIK_TRAIN" >&2
    exit 1
fi

# Order: fastest → slowest. chronos_bolt_tiny skipped (already done).
MODELS=(moirai2 chronos2 tirex timesfm25)
HORIZONS=(7 14 28)
HARDWARE="M_SERIES_MAC"

TOTAL_JOBS=$(( ${#MODELS[@]} * ${#HORIZONS[@]} ))

LOG_DIR="$REPO_ROOT/logs/rohlik_resume_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

TOTAL=0
FAILED=0

echo "=== Rohlik full-series RESUME (5,390 series) ==="
echo "Models: ${MODELS[*]}"
echo "Horizons: ${HORIZONS[*]}"
echo "TIREX_FORCE_CPU=$TIREX_FORCE_CPU"
echo "Logs: $LOG_DIR"
echo "Started: $(date)"
echo ""

for model in "${MODELS[@]}"; do
    for horizon in "${HORIZONS[@]}"; do
        TOTAL=$((TOTAL + 1))
        tag="${model}_rohlik_h${horizon}"
        log="$LOG_DIR/$tag.log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$TOTAL/$TOTAL_JOBS] $tag"

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
echo "Finished: $(date)"
echo "Logs: $LOG_DIR"
echo ""
echo "Next:"
echo "  python tools/export_mlflow_to_csv.py --out benchmark/results/local_fm_sweep.csv"
echo "  Rscript analysis/meta_regression.R"
