# Release Notes: v1.19 IJF Submission Prep

Release commit: recorded in the release package `COMMIT.txt`.

Local package target:
`release/zenodo-v1.19-ijf-submission-prep.zip`

## Summary

v1.19 addresses the remaining high-probability IJF reviewer objections before
submission.  It adds a richer-feature LightGBM sensitivity on the same M5
100-series matched panel, adds a prespecified-comparator sensitivity against
tuned recursive LightGBM, moves the unmatched Source B grid out of the main
text, and tightens reviewer-facing wording around fev-bench, hardware, and
provenance.

## What Changed

- Added `lightgbm_rich_tuned` to the Source B matched-panel runner and report
  pipeline.
- Ran `lightgbm_rich_tuned` on the M5 top-volume 100-series panel at
  h=7, 14, and 28 with 10 validation-origin tuning trials.
- Updated Source B best-baseline contrasts.  The richer-feature LightGBM
  becomes the best observed M5 baseline at h=14 and h=28, but Chronos-2 remains
  lower with bootstrap intervals excluding zero.
- Added prespecified-comparator contrasts against `lightgbm_tuned_cov` in all
  nine Source B dataset-horizon cells.
- Updated M5 panel-scaled RMSSE sensitivity to include the richer-feature
  LightGBM baseline.
- Moved the unmatched per-series Source B grid from the main text to Appendix G.
- Shortened the `direct_scaled` anomaly discussion to a provenance note.
- Clarified that the fev-bench prediction-level rerun is against Seasonal Naive.
- Standardised local hardware wording to MacBook Air M3, 16 GB, MPS/CPU.
- Updated Data Availability and release wording to v1.19.

## Package Audit

The Zenodo-ready archive contains:

- `manuscript/demand-forecasting-ijf-submission-prep-v1.19.pdf`
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
tools/build_v119_release.sh
```
