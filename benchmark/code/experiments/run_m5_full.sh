#!/usr/bin/env bash
# =============================================================================
# M5 sweep: 5 FMs × 3 horizons, tiered series counts.
#
# M5 has 30,490 series with ~70% zero-day fraction (intermittent demand).
# Full-series evaluation is critical for M5 because the metric sensitivity
# (per-series WAPE vs aggregate WAPE vs WRMSSE) depends on the long tail.
#
# Tier 1 (full 30,490): moirai2           (~7h total)
# Tier 2 (3,000):       chronos_bolt_tiny (~4h total)
# Tier 3 (3,000):       chronos2          (~7h total)
# Tier 4 (1,000):       tirex             (~7h total)
# Tier 5 (500):         timesfm25         (~10h total)
#
# Estimated total: ~35h on M-series MacBook. Run with nohup:
#   cd ~/Documents/Repos/large-scale-demand-forecasting-benchmark
#   nohup bash benchmark/code/experiments/run_m5_full.sh > m5_sweep.log 2>&1 &
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

M5_SALES="${M5_SALES_PATH:-data/raw/m5/sales_train_validation.csv}"
M5_CAL="${M5_CALENDAR_PATH:-data/raw/m5/calendar.csv}"
M5_PRICES="${M5_PRICES_PATH:-data/raw/m5/sell_prices.csv}"

if [[ ! -f "$M5_SALES" ]]; then
    echo "ERROR: M5 data not found at $M5_SALES" >&2
    exit 1
fi

HORIZONS=(7 14 28)
HARDWARE="M_SERIES_MAC"

# Model tiers: (model, max_series_flag)
# Moirai2 is fast enough for full M5. Others capped per speed tier.
declare -a TIERS=(
    "moirai2:"
    "chronos_bolt_tiny:3000"
    "chronos2:3000"
    "tirex:1000"
    "timesfm25:500"
)

TOTAL_JOBS=$(( ${#TIERS[@]} * ${#HORIZONS[@]} ))

LOG_DIR="$REPO_ROOT/logs/m5_sweep_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

DONE=0
FAILED=0

echo "=== M5 sweep (30,490 series, tiered) ==="
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
        tag="${model}_m5_h${horizon}"
        [[ -n "$max_series" ]] && tag="${tag}_n${max_series}"
        log="$LOG_DIR/$tag.log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$DONE/$TOTAL_JOBS] $tag"

        # shellcheck disable=SC2086
        "$PY" benchmark/code/experiments/run_gap_filling.py \
            --model "$model" \
            --dataset m5 \
            --horizon "$horizon" \
            --hardware "$HARDWARE" \
            --sales-path "$M5_SALES" \
            --calendar-path "$M5_CAL" \
            --prices-path "$M5_PRICES" \
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
