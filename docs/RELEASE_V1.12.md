# Release Notes: v1.12 TimesFM fev-bench WAPE Covariance Repair

Release commit: recorded in the release package `COMMIT.txt`.

Local package target:
`release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip`

## Summary

v1.12 completes the official fev-bench prediction-level WAPE covariance repair
for TimesFM 2.5.  The fev-bench retail repair now covers Seasonal Naive plus
four foundation-model reruns across all 20 retail tasks: Chronos-Bolt-Tiny,
Chronos-2, TiRex, and TimesFM 2.5.

This release also fixes the TimesFM 2.5 quantile export path in
`benchmark/code/models/foundation/timesfm25.py` and
`benchmark/code/experiments/run_fev_bench_official.py`.  Earlier TimesFM
official-run artifacts stored point forecasts in every quantile column, which
left WAPE and MASE usable but made SQL invalid.  The v1.12 official TimesFM
run uses `prediction_artifact_schema = v2_quantile_head` and stores the
continuous TimesFM quantile head.

## What Changed

- Completed `fev_v1_12_timesfm25_official_retail` for all 20 fev-bench retail
  tasks.
- Added TimesFM 2.5 to `analysis/fev_bench_prediction_report.py`.
- Added TimesFM 2.5 to `analysis/fev_bench_official_manifest.py`.
- Added TimesFM 2.5 to `analysis/fev_bench_wape_summary.py`.
- Generated TimesFM paired WAPE units, task-level contrasts, bootstrap draws,
  and empirical covariance matrices:
  - `analysis/figures/fev_timesfm25_paired_wape_units.csv`
  - `analysis/figures/fev_timesfm25_paired_wape_contrasts.csv`
  - `analysis/figures/fev_timesfm25_paired_wape_bootstrap_draws.csv`
  - `analysis/figures/fev_timesfm25_paired_wape_covariance.csv`
  - `analysis/figures/fev_timesfm25_paired_wape_covariance_long.csv`
- Regenerated the fev-bench official run manifest, model coverage summary, and
  bootstrap artifact manifest.
- Added a Source B integrity gate summary that records which legacy Source B
  issues remain failed or blocked by design, and which matched-panel repair
  gates have passed.
- Stabilized the Source B matched-panel report outputs: generated CSVs are
  sorted deterministically, and bootstrap resampling uses fixed dataset-split
  seeds so repeated runs and different `--runs` orderings reproduce identical
  Source B report artifacts.
- Updated the manuscript, README, ARTIFACTS, and REPRODUCING instructions.

## Main Results

TimesFM 2.5 official fev-bench WAPE repair against Seasonal Naive:

| Quantity | Value |
| --- | ---: |
| Tasks | 20 |
| Paired series-window units | 179,258 |
| Valid paired units | 177,512 |
| Median log-ratio | -0.282 |
| Mean log-ratio | -0.319 |
| Median FM/baseline ratio | 0.754 |
| Point estimates favouring TimesFM | 20/20 |
| Bootstrap intervals excluding zero in TimesFM direction | 19/20 |

Negative log-ratios favour the foundation model.  The empirical covariance
matrix is 20 by 20 over task-level WAPE log-ratios.

## Scope

This is a metric-specific prediction-level repair for fev-bench retail WAPE
against Seasonal Naive.  It does not repair SQL or MASE covariance, GIFT-Eval,
stronger best-baseline comparisons, GPU throughput, covariate-aware FM
variants, or additional independent benchmark suites.  TiRex remains WAPE-only
in this repair because its official rerun stores point forecasts in quantile
columns.  TimesFM 2.5 now uses the continuous quantile head, but the empirical
covariance artifact reported here still targets paired WAPE log-ratios.

Raw prediction parquet trees under `benchmark/results/fev_bench_official/` are
not versioned in git and are not included in the release package.  The release
contains scripts, manifests, generated summaries, and covariance artifacts
needed to audit and reproduce the reported WAPE repair.

## Package Audit

The Zenodo-ready archive contains:

- `manuscript/demand-forecasting-timesfm-fev-bench-wape-covariance-repair-v1.12.pdf`
- `replication/` with source, tests, derived analysis artifacts, manifests, and
  release documentation
- `replication/docs/PUBLICATION_HANDOFF_V1.12.md` with the final GitHub/Zenodo
  publication checklist
- `COMMIT.txt` with the source commit used to build the package
- `CHECKSUMS.txt` with SHA-256 hashes for packaged files

The package intentionally excludes `.git/`, `release/`, `data/raw/`, `mlruns/`,
`logs/`, Python cache directories, `.pytest_cache/`, root-level `*.log` files,
`.DS_Store`, local `.env` files, model checkpoint formats, private
`Umowa*.pdf` files, full
`benchmark/results/fev_bench_official/` prediction parquet trees, and the
untracked local `source_b_v1_11_timesfm25_m5_rohlik_100_batched` prediction
tree.  It also excludes superseded working notes such as
`analysis/baseline_results.md` and `paper/drafts/`; the auditable manuscript
source is the LaTeX tree under `paper/latex/`.

Publication readiness is checked separately with
`python3 tools/audit_publication_readiness.py`.  Run it once before changing
repository visibility, then rerun with `--require-public` after making GitHub
public.  After the GitHub release is created, `python3 tools/audit_github_release.py`
checks that tag `v1.12` and the uploaded zip asset match the local package.
