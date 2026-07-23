# Release Notes: v1.16 Submission Framing Repair

Release commit: recorded in the release package `COMMIT.txt`.

Local package target:
`release/zenodo-v1.16-submission-framing-repair.zip`

## Summary

v1.16 restructures the manuscript for journal submission.  The scientific
identity is now a matched-panel benchmark study with public-benchmark
extraction, not a systematic review or confirmatory meta-analysis.

The main evidence hierarchy is:

1. Source B matched-panel experiments on M5, Rohlik v2, and Favorita with
   paired series-bootstrap covariance.
2. Prediction-level fev-bench WAPE reruns with empirical covariance matrices.
3. Descriptive fev-bench and GIFT-Eval extraction used to document
   metric-specific public-benchmark patterns and the extractability gap.

## What Changed

- Rewrote the title, abstract, introduction, and conclusion around matched
  panels and public benchmarks.
- Degraded Source A weighted diagnostics to supplemental audit artifacts.
- Removed PRISMA/systematic-review branding from the flow figure and main-text
  framing.
- Clarified that the Source B baseline comparison is against pragmatic
  fixed-feature LightGBM systems, not competition-grade M5 feature engineering.
- Updated Rohlik v2 data availability.
- Clarified M5 zero prevalence as series-day zero fraction.
- Reconciled the M5 fixed-budget direct-vs-recursive h=7 value to +16.8%.
- Preserved the v1.15 M5 200-trial LightGBM sensitivity artifact and release
  checks.

## Scope

This release is a manuscript-structure and framing repair.  It does not add new
experiments beyond v1.15.  Rohlik/Favorita 200-trial LightGBM stress tests,
covariate-aware FM variants, richer competition-grade LightGBM feature sets,
larger panels, and GPU throughput remain future work.

## Package Audit

The Zenodo-ready archive contains:

- `manuscript/demand-forecasting-submission-framing-repair-v1.16.pdf`
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
tools/build_v116_release.sh
```
