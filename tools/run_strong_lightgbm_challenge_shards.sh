#!/usr/bin/env bash
set -euo pipefail

TRIALS="${LIGHTGBM_TUNING_TRIALS:-200}"
MAX_SERIES="${SOURCE_B_MAX_SERIES:-100}"
SEED="${SOURCE_B_SEED:-20260714}"
TRAIN_WINDOW_DAYS="${SOURCE_B_TRAIN_WINDOW_DAYS:-365}"
SERIES_SELECTION="${SOURCE_B_SERIES_SELECTION:-top_volume}"

run_shard() {
  local dataset="$1"
  local horizon="$2"
  local model="$3"
  local run_id="source_b_v1_15_${dataset}_h${horizon}_${model}_${TRIALS}trial"

  python3 benchmark/code/experiments/run_source_b_paired_panel.py \
    --datasets "$dataset" \
    --models "$model" \
    --horizons "$horizon" \
    --max-series "$MAX_SERIES" \
    --series-selection "$SERIES_SELECTION" \
    --seed "$SEED" \
    --train-window-days "$TRAIN_WINDOW_DAYS" \
    --lightgbm-tuning-trials "$TRIALS" \
    --run-id "$run_id"
}

for horizon in 7 14 28; do
  run_shard m5 "$horizon" lightgbm_tuned_cov
  run_shard m5 "$horizon" lightgbm_tuned_direct
done

for dataset in rohlik favorita; do
  run_shard "$dataset" 7 lightgbm_tuned_cov
  run_shard "$dataset" 7 lightgbm_tuned_direct
done
