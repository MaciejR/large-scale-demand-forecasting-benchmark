#!/usr/bin/env bash
# =============================================================================
# Phase 1 expansion sweep: 5 FMs × 3 datasets × 3 horizons + Chronos-2 covariates.
#
# Total: 54 jobs (45 univariate + 9 Chronos-2 with covariates).
# Target: Apple M-series MacBook, PyTorch MPS backend, full-series evaluation.
#
# This replaces the original run_local_fm_sweep.sh which only ran 2 FMs at
# n=100 sampled series. The expansion sweep runs all 5 FMs at full series
# count to produce proper bootstrap SEs for the k≥50 meta-regression.
#
# FMs under test:
#   1. chronos_bolt_tiny  (~9 M params, T5, univariate)
#   2. tirex              (~35 M params, xLSTM, univariate)
#   3. chronos2           (~120 M params, T5, univariate + covariates)
#   4. moirai2            (~11 M params, MoE, univariate)
#   5. timesfm25          (~200 M params, decoder-only, univariate)
#
# Datasets: M5, Favorita, Rohlik v2 — same as original sweep.
# Horizons: 7, 14, 28 days.
#
# Usage:
#   # 1. Set up environment
#   export FM_LOCAL_VENV=~/venvs/fm-local
#   $FM_LOCAL_VENV/bin/pip install -r benchmark/code/requirements-local-fm.txt
#
#   # 2. Set data paths
#   export M5_SALES_PATH=/path/to/sales_train_validation.csv
#   export M5_CALENDAR_PATH=/path/to/calendar.csv
#   export M5_PRICES_PATH=/path/to/sell_prices.csv      # required for Chronos-2 covariates
#   export FAVORITA_TRAIN_PATH=/path/to/train.csv
#   export FAVORITA_OIL_PATH=/path/to/oil.csv            # optional covariates
#   export FAVORITA_HOLIDAYS_PATH=/path/to/holidays.csv  # optional covariates
#   export FAVORITA_STORES_PATH=/path/to/stores.csv      # optional covariates
#   export ROHLIK_TRAIN_PATH=/path/to/train.csv
#   export ROHLIK_CALENDAR_PATH=/path/to/calendar.csv    # optional covariates
#
#   # 3. Run (choose phase)
#   PHASE=smoke bash benchmark/code/experiments/run_expansion_sweep.sh   # 500 series, verify
#   PHASE=full  bash benchmark/code/experiments/run_expansion_sweep.sh   # full series, production
#
# Expected wall times (M3 Pro 16GB, full series):
#   Rohlik (5,390 series):   ~1-3h per FM
#   Favorita (30,000 series): ~6-12h per FM
#   M5 (30,490 series):      ~12-24h per FM (intermittent = slower rolling windows)
#   Total: 3-7 days for all 54 jobs
#
# Output: MLflow runs + logs. Export to CSV with:
#   python benchmark/code/tools/export_mlflow_to_csv.py
# =============================================================================

set -euo pipefail

VENV="${FM_LOCAL_VENV:-$HOME/venvs/fm-local}"
if [[ ! -x "$VENV/bin/python" ]]; then
    echo "ERROR: venv not found at $VENV" >&2
    echo "Create with: python3.11 -m venv $VENV && \\" >&2
    echo "             $VENV/bin/pip install -r benchmark/code/requirements-local-fm.txt" >&2
    exit 1
fi
PY="$VENV/bin/python"

# Phase selection: "smoke" = 500 series (verify scripts), "full" = all series.
PHASE="${PHASE:-smoke}"
case "$PHASE" in
    smoke) MAX_SERIES_ARG="--max-series 500" ;;
    full)  MAX_SERIES_ARG="" ;;
    *)     echo "ERROR: PHASE must be 'smoke' or 'full'" >&2; exit 1 ;;
esac

HARDWARE="M_SERIES_MAC"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/benchmark/code:${PYTHONPATH:-}"

# All 5 FMs for univariate runs.
MODELS_UNIVARIATE=(chronos_bolt_tiny tirex chronos2 moirai2 timesfm25)
# Chronos-2 is the only FM supporting covariates.
MODELS_COVARIATES=(chronos2)

DATASETS=(rohlik favorita m5)
HORIZONS=(7 14 28)

LOG_DIR="$REPO_ROOT/logs/expansion_sweep_${PHASE}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
echo "=== Expansion sweep (phase=$PHASE) ==="
echo "Logs: $LOG_DIR"
echo "Jobs: ${#MODELS_UNIVARIATE[@]}×${#DATASETS[@]}×${#HORIZONS[@]} univariate + ${#MODELS_COVARIATES[@]}×${#DATASETS[@]}×${#HORIZONS[@]} covariates"
echo ""

TOTAL=0
FAILED=0

dataset_args() {
    local dataset="$1" with_cov="${2:-no}"
    local -a extra=()
    case "$dataset" in
        m5)
            extra+=(--sales-path "$M5_SALES_PATH" --calendar-path "$M5_CALENDAR_PATH")
            if [[ "$with_cov" == "yes" && -n "${M5_PRICES_PATH:-}" ]]; then
                extra+=(--prices-path "$M5_PRICES_PATH")
            fi
            ;;
        favorita)
            extra+=(--sales-path "$FAVORITA_TRAIN_PATH")
            if [[ "$with_cov" == "yes" ]]; then
                [[ -n "${FAVORITA_OIL_PATH:-}" ]] && extra+=(--oil-path "$FAVORITA_OIL_PATH")
                [[ -n "${FAVORITA_HOLIDAYS_PATH:-}" ]] && extra+=(--holidays-path "$FAVORITA_HOLIDAYS_PATH")
                [[ -n "${FAVORITA_STORES_PATH:-}" ]] && extra+=(--stores-path "$FAVORITA_STORES_PATH")
            fi
            ;;
        rohlik)
            extra+=(--sales-path "$ROHLIK_TRAIN_PATH")
            if [[ "$with_cov" == "yes" && -n "${ROHLIK_CALENDAR_PATH:-}" ]]; then
                extra+=(--calendar-path "$ROHLIK_CALENDAR_PATH")
            fi
            ;;
    esac
    echo "${extra[@]}"
}

run_one() {
    local model="$1" dataset="$2" horizon="$3" cov_flag="${4:-}"
    local tag="${model}_${dataset}_h${horizon}${cov_flag:+_cov}"
    local log="$LOG_DIR/$tag.log"

    TOTAL=$((TOTAL + 1))
    echo "[$(date +%H:%M:%S)] [$TOTAL] $tag"

    local with_cov="no"
    [[ -n "$cov_flag" ]] && with_cov="yes"
    local ds_args
    ds_args=$(dataset_args "$dataset" "$with_cov")

    # shellcheck disable=SC2086
    "$PY" benchmark/code/experiments/run_gap_filling.py \
        --model "$model" \
        --dataset "$dataset" \
        --horizon "$horizon" \
        --hardware "$HARDWARE" \
        $MAX_SERIES_ARG \
        $cov_flag \
        $ds_args 2>&1 | tee "$log" || {
            echo "FAIL: $tag — see $log" >&2
            FAILED=$((FAILED + 1))
        }
    echo ""
}

# ---- Phase A: Univariate runs (45 jobs) ----
echo "=== Univariate runs ==="
for model in "${MODELS_UNIVARIATE[@]}"; do
    for dataset in "${DATASETS[@]}"; do
        for horizon in "${HORIZONS[@]}"; do
            run_one "$model" "$dataset" "$horizon"
        done
    done
done

# ---- Phase B: Chronos-2 with covariates (9 jobs) ----
echo "=== Covariate runs (Chronos-2 only) ==="
for model in "${MODELS_COVARIATES[@]}"; do
    for dataset in "${DATASETS[@]}"; do
        for horizon in "${HORIZONS[@]}"; do
            run_one "$model" "$dataset" "$horizon" "--with-covariates"
        done
    done
done

echo ""
echo "=== Sweep complete ==="
echo "Total: $TOTAL jobs, $FAILED failed"
echo "Logs: $LOG_DIR"
echo ""
echo "Next steps:"
echo "  1. Export MLflow runs to CSV:"
echo "     python benchmark/code/tools/export_mlflow_to_csv.py"
echo "  2. Run meta-regression:"
echo "     Rscript analysis/meta_regression.R"
