# Release Notes: v1.20 IJF Submission Package

Release commit: recorded in the release package `COMMIT.txt`.

Local package target:
`release/zenodo-v1.20-ijf-submission-package.zip`

## Summary

v1.20 is the final IJF submission package on top of v1.19.  It preserves the
v1.19 analyses and includes the post-v1.19 wording proofread so that the
manuscript PDF, package manifest, `COMMIT.txt`, GitHub tag, and Data
Availability text all point to the same source state.

## What Changed

- Preserves the v1.19 richer-feature M5 LightGBM sensitivity,
  prespecified-comparator sensitivity, M5 panel-scaled RMSSE sensitivity, and
  fev-bench Seasonal Naive clarification.
- Updates Data Availability and release wording to v1.20.
- Clarifies that Moirai/TiRex interval counts use unrounded bootstrap
  quantiles.
- Displays the Rohlik h=14 Moirai interval as `[-0.050, -0.002]` rather than a
  misleading rounded `[-0.050, -0.000]`.
- Clarifies that the 200-trial M5 envelope uses the original fixed feature set
  and does not include the separate richer-feature LightGBM check.
- Clarifies that Rohlik tuning selected configurations effectively equivalent
  to the fixed recursive defaults after rounding.

## Package Audit

The Zenodo-ready archive contains:

- `manuscript/demand-forecasting-ijf-submission-package-v1.20.pdf`
- `replication/` with source, tests, derived analysis artifacts, manifests,
  allow-listed M5 200-trial outputs, the M5 richer-feature LightGBM run, and
  release documentation
- `COMMIT.txt` with the source commit used to build the package
- `CHECKSUMS.txt` with SHA-256 hashes for packaged files

The package intentionally excludes `.git/`, `release/`, `data/raw/`, `mlruns/`,
`logs/`, Python cache directories, `.pytest_cache/`, root-level `*.log` files,
`.DS_Store`, local `.env` files, model checkpoint formats, private
`Umowa*.pdf` files, full `benchmark/results/fev_bench_official/` prediction
parquet trees, and local quarantine directories.

Build and audit locally with:

```bash
tools/build_v120_release.sh
```
