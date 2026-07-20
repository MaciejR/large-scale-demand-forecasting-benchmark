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
- `replication/docs/ZENODO_METADATA_V1.12.json` with the Zenodo metadata draft
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
`python3 tools/audit_publication_readiness.py`.  Run it with
`--require-public` after every package rebuild and GitHub release asset update.
`python3 tools/audit_github_release.py` checks that tag `v1.12` and the
uploaded zip asset metadata match the local package; add `--verify-download`
for the final gate that downloads the asset and compares its SHA-256 to the
local ZIP.
`python3 tools/audit_zenodo_metadata.py` checks that the Zenodo metadata draft
matches the package version, GitHub release URL, historical DOI relation, asset
name, commit-provenance note, packaged `CHECKSUMS.txt` note, and root
`.zenodo.json` metadata.
`python3 tools/audit_zenodo_upload_readiness.py` combines the GitHub release,
Zenodo metadata, package provenance, clean-tree, and pushed-HEAD checks.  Add
`--require-token` immediately before an API upload to verify that a Zenodo token
is present without printing it.
`python3 tools/audit_publication_log_v112.py` checks that
`docs/PUBLICATION_LOG_V1.12.md` has the required fields and that any recorded
commit or asset checksum matches the current package; after Zenodo publication,
add `--require-complete` to fail on remaining placeholders.
`python3 tools/zenodo_upload_v112.py --dry-run` validates the same package and
prints the planned Zenodo upload.  Without `--dry-run`, it creates or updates an
unpublished draft and appends the outer ZIP SHA-256 to the Zenodo record notes;
the irreversible publish action requires an explicit `--publish` flag.  Add
`--output-json` to persist the Zenodo response for the publication-log helper.
Sandbox upload tests use `ZENODO_SANDBOX_ACCESS_TOKEN` or `ZENODO_SANDBOX_TOKEN`
via `python3 tools/zenodo_upload_v112.py --sandbox`, keeping sandbox credentials
separate from production Zenodo credentials.
After Zenodo mints the v1.12 DOI, `python3 tools/apply_v112_zenodo_doi.py`
updates README, `CITATION.cff`, manuscript data availability text, and these
release notes from the GitHub-release citation to the archived DOI.
`python3 tools/update_publication_log_v112.py` reads the JSON output from
`tools/zenodo_upload_v112.py` and fills the publication log with the deposition
ID, record URL, DOI, current commit, and package SHA.
`tools/publish_v112_zenodo.sh` wraps the audited dry-run, draft, sandbox-draft,
and publish flows without bypassing the underlying readiness checks; it writes
the Zenodo response JSON but leaves publication-log edits to the explicit
`tools/update_publication_log_v112.py` step.
