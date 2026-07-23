# Release Notes: v1.17 IJF Submission Restructure

Release commit: recorded in the release package `COMMIT.txt`.

Local package target:
`release/zenodo-v1.17-ijf-submission-restructure.zip`

## Summary

v1.17 restructures the manuscript toward a journal-submission benchmark-study
identity.  The core paper is now organised around matched-panel Source B
experiments, prediction-level fev-bench reruns, and a short supporting
public-benchmark extraction.  Historical workload-weighted Source A model fits
remain reproducible in the repository but are no longer included in the
compiled manuscript.

The main evidence hierarchy is:

1. Source B matched-panel experiments on M5, Rohlik v2, and Favorita with
   paired series-bootstrap covariance.
2. M5 baseline stress tests: stratified intermittent panel and 200-trial
   LightGBM sensitivity within the fixed feature set.
3. Prediction-level fev-bench WAPE reruns with empirical covariance matrices.
4. Supporting fev-bench and GIFT-Eval extraction used descriptively to document
   metric-specific public-benchmark patterns and the extractability gap.

## What Changed

- Removed Appendix D from the compiled manuscript; historical `rma.mv`/CR2/Q
  diagnostics remain generated artifacts, not submission text.
- Reframed Section 6 as supporting public-benchmark evidence rather than a
  primary meta-analytic result.
- Degraded cost from a first-order research question to descriptive deployment
  accounting because the legacy Azure ledger is not fully reconciled.
- Updated the research-question numbering to RQ1 accuracy, RQ2 moderators, and
  RQ3 practitioner guidance.
- Updated Data Availability and release wording to v1.17.
- Kept v1.16 as a historical release rather than overwriting its package.

## Scope

This release is a manuscript-structure and framing repair.  It does not add new
experiments beyond the v1.15/v1.16 experimental artifacts.  Richer
competition-grade LightGBM feature sets, Rohlik/Favorita 200-trial LightGBM
stress tests, covariate-aware FM variants, larger panels, and GPU throughput
remain future work.

## Package Audit

The Zenodo-ready archive contains:

- `manuscript/demand-forecasting-ijf-submission-restructure-v1.17.pdf`
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
tools/build_v117_release.sh
```
