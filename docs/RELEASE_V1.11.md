# Release Notes: v1.11 Source B TimesFM Matched-Panel Extension

Release commit: recorded in the release package `COMMIT.txt`.

Local package target:
`release/zenodo-v1.11-source-b-timesfm-matched-panel-extension.zip`

## Summary

v1.11 completes the local Source B matched-panel coverage for TimesFM 2.5 on
M5 and Rohlik.  The Source B paired-panel repair now contains 45
FM-vs-best-baseline WAPE log-ratio contrasts: five local FMs across M5,
Rohlik, and Favorita at horizons 7, 14, and 28.

The extension does not change the primary Source A reanalysis.  It strengthens
the local matched-panel sensitivity analysis by removing the previous
TimesFM-on-M5/Rohlik gap and regenerating the Source B shared-bootstrap
covariance matrix as a 45 by 45 matrix.

## What Changed

- Completed `source_b_v1_11_timesfm25_m5_rohlik_100_batched`.
- Added TimesFM 2.5 matched-panel M5/Rohlik contrasts to
  `analysis/figures/source_b_paired_panel_fm_vs_best_baseline.csv`.
- Regenerated Source B matched-panel bootstrap draws, per-series metrics,
  run ledger, and log-ratio covariance outputs.
- Updated the manuscript, README, ARTIFACTS, and REPRODUCING instructions.

## Main Results

TimesFM 2.5 matched-panel aggregate-WAPE log-ratios:

| Dataset | h | log-ratio | 95% bootstrap CI |
| --- | ---: | ---: | ---: |
| M5 | 7 | -0.067 | [-0.085, -0.052] |
| M5 | 14 | -0.071 | [-0.091, -0.052] |
| M5 | 28 | -0.079 | [-0.106, -0.052] |
| Rohlik | 7 | -0.040 | [-0.063, -0.015] |
| Rohlik | 14 | -0.048 | [-0.074, -0.021] |
| Rohlik | 28 | -0.060 | [-0.089, -0.031] |
| Favorita | 7 | 0.017 | [-0.014, 0.052] |
| Favorita | 14 | 0.001 | [-0.034, 0.039] |
| Favorita | 28 | 0.006 | [-0.036, 0.051] |

Negative log-ratios favour the foundation model.

## Scope

This is a local 100-series matched-panel Source B extension.  It remains a
sensitivity analysis, not a confirmatory cross-benchmark result.  GPU
throughput, larger workloads, covariate-aware FM variants, SQL/MASE
prediction-level covariance, GIFT-Eval covariance, and stronger Source A
best-baseline covariance remain future work.
