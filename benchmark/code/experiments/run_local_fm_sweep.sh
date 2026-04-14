#!/usr/bin/env bash
# Local MPS FM sweep for §5.4.3 (1+3 hybrid sensitivity run).
#
# Sweep: 3 models x 3 datasets x 3 horizons = 27 jobs.
# Target hardware: Apple M-series MacBook, PyTorch MPS backend.
# Cost bucket: M_SERIES_MAC ($0.006/hr marginal electricity, poland grid).
#
# Usage:
#   export FM_LOCAL_VENV=~/venvs/fm-local
#   export M5_SALES_PATH=...       # sales_train_validation.csv
#   export M5_CALENDAR_PATH=...    # calendar.csv
#   export M5_PRICES_PATH=...      # sell_prices.csv (optional for FM)
#   export FAVORITA_TRAIN_PATH=...
#   export ROHLIK_TRAIN_PATH=...
#   bash benchmark/code/experiments/run_local_fm_sweep.sh
#
# Wall-time note: rolling_forecast iterates per-series per-window. With
# --max-series=500 and ~48 windows/dataset/horizon, expect ~3-6h total
# on an M3 Pro for the full 27-job sweep. Increase to 1000 only if the
# first dataset finishes in under an hour.
#
# Output: MLflow runs under experiment "meta-analysis-gap-filling",
# tagged hardware=M_SERIES_MAC. Results feed §5.4.6 cross-protocol
# comparison and Figure 6.4 consumer-HW Pareto frontier.

set -euo pipefail

VENV="${FM_LOCAL_VENV:-$HOME/venvs/fm-local}"
if [[ ! -x "$VENV/bin/python" ]]; then
    echo "ERROR: venv not found at $VENV" >&2
    echo "Create with: python3.11 -m venv $VENV && \\" >&2
    echo "             $VENV/bin/pip install -r benchmark/code/requirements-local-fm.txt" >&2
    exit 1
fi
PY="$VENV/bin/python"

MAX_SERIES="${MAX_SERIES:-100}"
HARDWARE="M_SERIES_MAC"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/benchmark/code:${PYTHONPATH:-}"

MODELS=(chronos_bolt_tiny tirex)
# TabPFN-TS dropped from Source B: on-device inference costs ~60 s per
# forecast window on M-series CPU (~100x Chronos-Bolt-Tiny), making a
# 48-window rolling-origin sweep infeasible inside the §5.4.3 budget.
# Documented as a Source B finding; TabPFN-TS still appears in Source A.
DATASETS=(m5 favorita rohlik)
HORIZONS=(7 14 28)

LOG_DIR="$REPO_ROOT/logs/local_fm_sweep_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
echo "Logs: $LOG_DIR"

run_one() {
    local model="$1" dataset="$2" horizon="$3"
    local tag="${model}_${dataset}_h${horizon}"
    local log="$LOG_DIR/$tag.log"
    echo "[$(date +%H:%M:%S)] $tag"

    local -a extra=()
    case "$dataset" in
        m5)
            extra+=(--sales-path "$M5_SALES_PATH" --calendar-path "$M5_CALENDAR_PATH")
            [[ -n "${M5_PRICES_PATH:-}" ]] && extra+=(--prices-path "$M5_PRICES_PATH")
            ;;
        favorita)
            extra+=(--sales-path "$FAVORITA_TRAIN_PATH")
            ;;
        rohlik)
            extra+=(--sales-path "$ROHLIK_TRAIN_PATH")
            ;;
    esac

    "$PY" benchmark/code/experiments/run_gap_filling.py \
        --model "$model" \
        --dataset "$dataset" \
        --horizon "$horizon" \
        --hardware "$HARDWARE" \
        --max-series "$MAX_SERIES" \
        "${extra[@]}" 2>&1 | tee "$log"
}

for model in "${MODELS[@]}"; do
    for dataset in "${DATASETS[@]}"; do
        for horizon in "${HORIZONS[@]}"; do
            run_one "$model" "$dataset" "$horizon" || {
                echo "FAIL: $model/$dataset/h$horizon — see $LOG_DIR" >&2
            }
        done
    done
done

echo "Sweep complete. Logs in $LOG_DIR"
