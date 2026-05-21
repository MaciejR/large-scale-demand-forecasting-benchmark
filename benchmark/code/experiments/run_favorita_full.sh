#!/usr/bin/env bash
# =============================================================================
# Favorita sweep: 5 FMs × 3 horizons, tiered series counts.
#
# Tier 1 (full 29,753): moirai2           (~7h total)
# Tier 2 (3,000):       chronos_bolt_tiny (~4h total)
# Tier 3 (3,000):       chronos2          (~7h total)
# Tier 4 (1,000):       tirex             (~7h total)
# Tier 5 (500):         timesfm25         (~10h total)
#
# Estimated total: ~35h on M-series MacBook. Run with nohup:
#   cd ~/Documents/Repos/large-scale-demand-forecasting-benchmark
#   nohup bash benchmark/code/experiments/run_favorita_full.sh > favorita_sweep.log 2>&1 &
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
export TIREX_FORCE_CPU=1

FAV_TRAIN="${FAVORITA_TRAIN_PATH:-data/raw/favorita/train.csv}"
FAV_OIL="${FAVORITA_OIL_PATH:-data/raw/favorita/oil.csv}"
FAV_HOLIDAYS="${FAVORITA_HOLIDAYS_PATH:-data/raw/favorita/holidays_events.csv}"
FAV_STORES="${FAVORITA_STORES_PATH:-data/raw/favorita/stores.csv}"
FAV_TX="${FAVORITA_TX_PATH:-data/raw/favorita/transactions.csv}"

if [[ ! -f "$FAV_TRAIN" ]]; then
    echo "ERROR: Favorita data not found at $FAV_TRAIN" >&2
    exit 1
fi

HORIZONS=(7 14 28)
HARDWARE="M_SERIES_MAC"

# Model tiers: (model, max_series_flag)
# Empty max_series = full dataset
declare -a TIERS=(
    "moirai2:"
    "chronos_bolt_tiny:3000"
    "chronos2:3000"
    "tirex:1000"
    "timesfm25:500"
)

TOTAL_JOBS=$(( ${#TIERS[@]} * ${#HORIZONS[@]} ))

LOG_DIR="$REPO_ROOT/logs/favorita_sweep_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

DONE=0
FAILED=0

echo "=== Favorita sweep (29,753 series, tiered) ==="
echo "Tiers: ${TIERS[*]}"
echo "Horizons: ${HORIZONS[*]}"
echo "TIREX_FORCE_CPU=$TIREX_FORCE_CPU"
echo "Logs: $LOG_DIR"
echo "Started: $(date)"
echo ""

for tier in "${TIERS[@]}"; do
    model="${tier%%:*}"
    max_series="${tier#*:}"

    max_flag=""
    if [[ -n "$max_series" ]]; then
        max_flag="--max-series $max_series"
    fi

    for horizon in "${HORIZONS[@]}"; do
        DONE=$((DONE + 1))
        tag="${model}_favorita_h${horizon}"
        [[ -n "$max_series" ]] && tag="${tag}_n${max_series}"
        log="$LOG_DIR/$tag.log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$DONE/$TOTAL_JOBS] $tag"

        # shellcheck disable=SC2086
        "$PY" benchmark/code/experiments/run_gap_filling.py \
            --model "$model" \
            --dataset favorita \
            --horizon "$horizon" \
            --hardware "$HARDWARE" \
            --sales-path "$FAV_TRAIN" \
            --oil-path "$FAV_OIL" \
            --holidays-path "$FAV_HOLIDAYS" \
            --stores-path "$FAV_STORES" \
            --transactions-path "$FAV_TX" \
            $max_flag \
            2>&1 | tee "$log" || {
                echo "FAIL: $tag — see $log" >&2
                FAILED=$((FAILED + 1))
            }
        echo ""
    done
done

echo "=== Done: $DONE jobs, $FAILED failed ==="
echo "Finished: $(date)"
echo "Logs: $LOG_DIR"
echo ""
echo "Next:"
echo "  python tools/export_mlflow_to_csv.py --out benchmark/results/local_fm_sweep.csv"
echo "  Rscript analysis/meta_regression.R"
