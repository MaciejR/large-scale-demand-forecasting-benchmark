# Release Notes: v1.18 IJF Consistency and M5 Scaled-Metric Check

Release commit: recorded in the release package `COMMIT.txt`.

Local package target:
`release/zenodo-v1.18-ijf-consistency-scaled-m5.zip`

## Summary

v1.18 is a consistency and reviewer-risk repair on top of v1.17.  It corrects
remaining claim/table mismatches in the matched-panel Source B discussion,
removes the duplicated cloud-GPU cost scatter from the compiled manuscript, and
adds an M5 matched-panel scaled-error sensitivity.

The new M5 sensitivity is not official M5 WRMSSE.  Official WRMSSE is defined on
the full coherent hierarchy, while the local matched panel contains 100
bottom-level item-store series.  The added check uses origin-specific
last-28-day dollar weights and RMSSE scales estimated from history available
before each forecast origin.

## What Changed

- Corrected Moirai 2.0-Small language from "all nine" to "eight of nine" point
  estimates, matching Favorita h=28 in Table 9.
- Corrected the Favorita close-call paragraph: best observed baselines are
  recursive LightGBM at h=7, tuned recursive LightGBM at h=14, and tuned direct
  LightGBM at h=28.
- Added a Table 9 caveat that the best-baseline column is selected by observed
  panel WAPE and bootstrap intervals condition on that selection.
- Added `analysis/source_b_m5_panel_scaled_metric.py` plus generated CSV and
  LaTeX artifacts for the M5 panel-scaled RMSSE sensitivity.
- Removed the duplicated cloud-GPU cost scatter from the manuscript text and
  kept cost accounting descriptive until a measured GPU ledger exists.
- Weakened Rohlik leakage wording: Rohlik v2 is useful because no documented
  pretraining exposure was found in the evaluated model papers, but this is not
  a formal pretraining audit.
- Clarified that the legacy Favorita `direct_scaled` anomaly remains a
  provenance issue; the matched-panel protocol check resolves only the new
  matched-panel same-tree-count behaviour.
- Updated Data Availability and release wording to v1.18.

## Package Audit

The Zenodo-ready archive contains:

- `manuscript/demand-forecasting-ijf-consistency-scaled-m5-v1.18.pdf`
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
tools/build_v118_release.sh
```
