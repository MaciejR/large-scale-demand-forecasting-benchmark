#!/usr/bin/env bash
# =============================================================================
# Master launcher: M5 → Favorita full FM sweep (tiered max_series).
#
# Runs run_m5_full.sh then run_favorita_full.sh sequentially.
# Rohlik is already complete — skipped.
#
# Tier summary (both datasets):
#   moirai2           full series   (~14h total)
#   chronos_bolt_tiny 3,000 series  (~8h total)
#   chronos2          3,000 series  (~15h total)
#   tirex             1,000 series  (~14h total)
#   timesfm25         500 series    (~20h total)
#   TOTAL:                          ~71h (~3 days)
#
# Usage (run from repo root):
#   nohup bash benchmark/code/experiments/run_full_fm_sweep.sh \
#     > logs/full_fm_sweep.log 2>&1 &
#   echo $!                    # save PID to kill if needed
#   tail -f logs/full_fm_sweep.log
#
# After completion:
#   python tools/export_mlflow_to_csv.py \
#     --out benchmark/results/local_fm_sweep.csv
#   Rscript analysis/meta_regression.R
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SCRIPTS="$REPO_ROOT/benchmark/code/experiments"

VENV="${FM_LOCAL_VENV:-$HOME/venvs/fm-local}"
if [[ ! -x "$VENV/bin/python" ]]; then
    echo "ERROR: venv not found at $VENV" >&2
    echo "Create with: python3.11 -m venv $VENV && \\" >&2
    echo "             $VENV/bin/pip install -r benchmark/code/requirements-local-fm.txt" >&2
    exit 1
fi

mkdir -p "$REPO_ROOT/logs"

echo "============================================================"
echo "Full FM sweep launcher"
echo "Started: $(date)"
echo "============================================================"
echo ""

echo ">>> Phase 1/2: M5 (30,490 series, tiered)"
bash "$SCRIPTS/run_m5_full.sh"
echo ""
echo ">>> Phase 1/2 done: $(date)"
echo ""

echo ">>> Phase 2/2: Favorita (29,753 series, tiered)"
bash "$SCRIPTS/run_favorita_full.sh"
echo ""
echo ">>> Phase 2/2 done: $(date)"
echo ""

echo "============================================================"
echo "All sweeps complete: $(date)"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Export results:"
echo "     python tools/export_mlflow_to_csv.py \\"
echo "       --out benchmark/results/local_fm_sweep.csv"
echo "  2. Rerun meta-regression:"
echo "     Rscript analysis/meta_regression.R"
echo "  3. Commit:"
echo "     git add benchmark/results/local_fm_sweep.csv analysis/figures/"
echo "     git commit -m 'meta-analysis: full FM sweep M5+Favorita (tiered)'"
