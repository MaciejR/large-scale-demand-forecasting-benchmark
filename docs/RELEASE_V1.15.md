# Release Notes: v1.15 M5 200-trial LightGBM Sensitivity

Release commit: recorded in the release package `COMMIT.txt`.

Local package target:
`release/zenodo-v1.15-m5-200trial-lightgbm-sensitivity.zip`

## Summary

v1.15 integrates the completed M5 top-volume 100-series 200-trial LightGBM
sensitivity check into the benchmark manuscript and replication materials.  The
new sensitivity addresses the reviewer-facing concern that the Source B M5
result could be an artefact of a 10-trial LightGBM tuning budget.

The M5 high-budget check reruns tuned recursive and tuned direct LightGBM with
200 validation-origin trials for horizons 7, 14, and 28.  The analysis then
recomputes paired series-bootstrap log-ratio contrasts between the existing
Source B M5 foundation-model outputs and the best observed 200-trial LightGBM
baseline envelope within each horizon.

## Main Results

Chronos-2 remains below the best observed high-budget LightGBM envelope on the
same M5 top-volume 100-series panel:

| Horizon | Best 200-trial baseline | Baseline WAPE | Chronos-2 WAPE | Log-ratio 95% CI |
| ---: | --- | ---: | ---: | --- |
| 7 | tuned recursive LightGBM | 0.313 | 0.294 | -0.063 [-0.077, -0.050] |
| 14 | tuned recursive LightGBM | 0.330 | 0.307 | -0.073 [-0.091, -0.058] |
| 28 | tuned direct LightGBM | 0.360 | 0.339 | -0.061 [-0.089, -0.032] |

The 200-trial envelope is selected by observed test aggregate WAPE, so it is a
sensitivity envelope rather than a pre-registered confirmatory selector.  The
reported bootstrap intervals condition on the selected baseline and do not
include selection uncertainty.  Because the envelope chooses the better
LightGBM variant on the test panel, it is conservative for the reported
FM-vs-baseline point effect.

## Included Artifacts

- `data/m5_200trial/artifact_manifest.json`
- `data/m5_200trial/m5_lightgbm_200trial_cell_summary.csv`
- `data/m5_200trial/m5_lightgbm_200trial_tuning_summary.csv`
- `data/m5_200trial/m5_lightgbm_200trial_best_baselines.csv`
- `data/m5_200trial/m5_lightgbm_200trial_fm_vs_best_high_budget_baseline.csv`
- `data/m5_200trial/m5_lightgbm_200trial_logratio_covariance.csv`
- `data/m5_200trial/m5_lightgbm_200trial_bootstrap_draws.csv`
- the six allow-listed complete M5 200-trial run directories under
  `benchmark/results/source_b_paired_panel/`

The partial exploratory directory
`source_b_v1_15_strong_lightgbm_200trial_top_volume_100` is excluded from the
manifest, git status, and release package.

## Scope

This release strengthens the M5 top-volume Source B baseline sensitivity.  It
does not extend 200-trial LightGBM tuning to Rohlik, Favorita, the M5
stratified panel, larger panels, GPU throughput, or covariate-aware foundation
model variants.  Those remain future stress tests.

## Package Audit

The Zenodo-ready archive contains:

- `manuscript/demand-forecasting-m5-200trial-lightgbm-sensitivity-v1.15.pdf`
- `replication/` with source, tests, derived analysis artifacts, manifests,
  allow-listed M5 200-trial run outputs, and release documentation
- `COMMIT.txt` with the source commit used to build the package
- `CHECKSUMS.txt` with SHA-256 hashes for packaged files

The package intentionally excludes `.git/`, `release/`, `data/raw/`, `mlruns/`,
`logs/`, Python cache directories, `.pytest_cache/`, root-level `*.log` files,
`.DS_Store`, local `.env` files, model checkpoint formats, private
`Umowa*.pdf` files, full `benchmark/results/fev_bench_official/` prediction
parquet trees, and local quarantine directories.

Build and audit locally with:

```bash
tools/build_v115_release.sh
```
