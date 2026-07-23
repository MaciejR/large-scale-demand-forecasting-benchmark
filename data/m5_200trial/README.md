# M5 LightGBM 200-trial sensitivity artifact

This directory contains the manifest and generated analysis tables for the
v1.15 M5 high-budget LightGBM sensitivity check.

The six complete run directories are allow-listed in
`artifact_manifest.json`. The earlier partial directory
`source_b_v1_15_strong_lightgbm_200trial_top_volume_100` is explicitly
excluded and must not be ingested into analysis tables.

Generated tables:

- `m5_lightgbm_200trial_cell_summary.csv`: one row per 200-trial LightGBM
  horizon/protocol run.
- `m5_lightgbm_200trial_tuning_summary.csv`: validation-selected trial and
  test-panel WAPE for each run.
- `m5_lightgbm_200trial_fm_vs_best_high_budget_baseline.csv`: paired
  series-bootstrap log-ratio contrasts between Source B M5 FMs and the
  best 200-trial LightGBM baseline by horizon.
- `m5_lightgbm_200trial_logratio_covariance.csv`: covariance matrix for the
  M5 FM-vs-high-budget-baseline bootstrap draws.

The primary metric is aggregate WAPE on the shared top-volume 100-series M5
panel. Mean per-series WAPE is retained as a sensitivity column because it
answers a different estimand.
