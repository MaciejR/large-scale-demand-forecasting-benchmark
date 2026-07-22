# Strong LightGBM Baseline Runbook

Purpose: address the reviewer-facing concern that the matched-panel Source B
baseline is a fixed-budget LightGBM rather than a stronger tuned baseline.

The manuscript currently reports 10-trial tuned recursive and direct LightGBM
variants on the shared 100-series panels.  A stronger run should keep the same
panel definition, horizons, origins, features, metrics, and bootstrap pipeline,
changing only the tuning budget and, in a separate sensitivity, the training
window.

## Primary Strong Baseline

Run 200-trial tuned recursive and direct LightGBM on the top-volume 100-series
panels:

```bash
python3 benchmark/code/experiments/run_source_b_paired_panel.py \
  --datasets m5 rohlik favorita \
  --models lightgbm_tuned_cov lightgbm_tuned_direct \
  --horizons 7 14 28 \
  --max-series 100 \
  --series-selection top_volume \
  --seed 20260714 \
  --train-window-days 365 \
  --lightgbm-tuning-trials 200 \
  --run-id source_b_v1_15_strong_lightgbm_200trial_top_volume_100
```

## M5 Stratified Sensitivity

Run the same stronger baselines on the harder M5 stratified panel used for the
Chronos-2 sensitivity:

```bash
python3 benchmark/code/experiments/run_source_b_paired_panel.py \
  --datasets m5 \
  --models lightgbm_tuned_cov lightgbm_tuned_direct \
  --horizons 7 14 28 \
  --max-series 100 \
  --series-selection stratified_volume_zero \
  --seed 20260714 \
  --train-window-days 365 \
  --lightgbm-tuning-trials 200 \
  --run-id source_b_v1_15_m5_stratified_strong_lightgbm_200trial_100
```

## Training-Window Sensitivity

The current runner interprets `--train-window-days` as a bounded rolling
history.  Use a large value to approximate full available history while
preserving the same validation-origin tuning design:

```bash
python3 benchmark/code/experiments/run_source_b_paired_panel.py \
  --datasets m5 rohlik favorita \
  --models lightgbm_tuned_cov lightgbm_tuned_direct \
  --horizons 7 14 28 \
  --max-series 100 \
  --series-selection top_volume \
  --seed 20260714 \
  --train-window-days 10000 \
  --lightgbm-tuning-trials 200 \
  --run-id source_b_v1_15_strong_lightgbm_200trial_full_history_100
```

## Acceptance Checks

After each run:

```bash
python3 benchmark/code/experiments/summarize_source_b_paired_panel.py
Rscript analysis/meta_regression.R
tools/build_manuscript_pdf.sh
tools/audit_manuscript_v112.sh
git diff --check
```

The manuscript should promote the 200-trial best-baseline result only if all
models are evaluated on the same series IDs, origins, target dates, and
aggregate-WAPE definition as the existing matched-panel Source B runs.
