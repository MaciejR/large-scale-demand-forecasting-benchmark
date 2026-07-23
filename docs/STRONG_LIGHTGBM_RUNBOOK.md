# Strong LightGBM Baseline Runbook

Purpose: address the reviewer-facing concern that the matched-panel Source B
baseline is a fixed-budget LightGBM rather than a stronger tuned baseline.

The manuscript reports 10-trial tuned recursive and direct LightGBM variants
on the shared M5, Rohlik, and Favorita 100-series panels.  The M5 top-volume
panel now also has completed 200-trial tuned recursive/direct sensitivity
runs.  Stronger runs should keep the same panel definition, horizons, origins,
features, metrics, and bootstrap pipeline, changing only the tuning budget and,
in a separate sensitivity, the training window.

## Completed M5 200-trial sensitivity

The completed allow-listed run directories are recorded in
`data/m5_200trial/artifact_manifest.json`:

| Horizon | Model | Aggregate WAPE | Mean WAPE | Runtime |
| ---: | --- | ---: | ---: | ---: |
| 7 | tuned recursive LightGBM | 0.312660 | 0.362288 | 696.96 s |
| 7 | tuned direct LightGBM | 0.320079 | 0.371022 | 4412.47 s |
| 14 | tuned recursive LightGBM | 0.330437 | 0.382942 | 816.91 s |
| 14 | tuned direct LightGBM | 0.331019 | 0.388352 | 2510.82 s |
| 28 | tuned recursive LightGBM | 0.372461 | 0.436099 | 838.11 s |
| 28 | tuned direct LightGBM | 0.360307 | 0.430000 | 1936.89 s |

Regenerate the analysis-ready tables and paired bootstrap contrasts with:

```bash
python3 tools/validate_m5_200trial_artifact.py
python3 analysis/source_b_m5_200trial_sensitivity.py --n-bootstrap 1000
```

The generated files are written to `data/m5_200trial/` and mirrored where the
manuscript build expects figure/table inputs:

- `analysis/figures/source_b_m5_200trial_best_baselines.csv`
- `analysis/figures/source_b_m5_200trial_fm_vs_best_high_budget_baseline.csv`

The earlier partial run directory
`source_b_v1_15_strong_lightgbm_200trial_top_volume_100` was moved to local
quarantine and is explicitly excluded from analysis.

## Primary Strong Baseline

To extend the same 200-trial stress test beyond M5, run tuned recursive and
direct LightGBM on the top-volume 100-series panels:

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
  --run-id source_b_v1_15_strong_lightgbm_200trial_top_volume_100_complete
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
python3 tools/validate_m5_200trial_artifact.py
python3 analysis/source_b_m5_200trial_sensitivity.py --n-bootstrap 1000
Rscript analysis/meta_regression.R
tools/build_manuscript_pdf.sh
tools/audit_manuscript_v112.sh
git diff --check
```

The manuscript should promote the 200-trial best-baseline result only if all
models are evaluated on the same series IDs, origins, target dates, and
aggregate-WAPE definition as the existing matched-panel Source B runs.

## Reviewer-Salient Challenge Shards

For an initial submission-facing stress test, run the reviewer-salient cells as
independent shards.  The runner writes per-cell tuning checkpoints named
`tuning_trials_<dataset>_h<horizon>_<model>.csv`, so an interrupted shard can
be launched again with the same `--run-id` and it will skip completed tuning
trials.

```bash
for dataset in m5 rohlik favorita; do
  for horizon in 7; do
    for model in lightgbm_tuned_cov lightgbm_tuned_direct; do
      python3 benchmark/code/experiments/run_source_b_paired_panel.py \
        --datasets "$dataset" \
        --models "$model" \
        --horizons "$horizon" \
        --max-series 100 \
        --series-selection top_volume \
        --seed 20260714 \
        --train-window-days 365 \
        --lightgbm-tuning-trials 200 \
        --run-id "source_b_v1_15_${dataset}_h${horizon}_${model}_200trial"
    done
  done
done

for horizon in 14 28; do
  for model in lightgbm_tuned_cov lightgbm_tuned_direct; do
    python3 benchmark/code/experiments/run_source_b_paired_panel.py \
      --datasets m5 \
      --models "$model" \
      --horizons "$horizon" \
      --max-series 100 \
      --series-selection top_volume \
      --seed 20260714 \
      --train-window-days 365 \
      --lightgbm-tuning-trials 200 \
      --run-id "source_b_v1_15_m5_h${horizon}_${model}_200trial"
  done
done
```

This challenge set covers all M5 horizons plus the shortest-horizon Rohlik and
Favorita cells.  It is intended to test whether the local FM advantage survives
a much larger LightGBM tuning budget on the cells most likely to draw reviewer
attention.
