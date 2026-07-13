# Zenodo v1.0 Release Package

This directory contains the local copy of the published Zenodo v1.0 upload for:

**When Do Foundation Models Pay Off for Retail Demand Forecasting? A Systematic
Review and Cross-Benchmark Meta-Analysis**

Author: Maciej Rubczynski
Affiliation: Independent researcher
Version: v1.0
Release date: 2026-07-13
Record: https://zenodo.org/records/21338004
DOI: https://doi.org/10.5281/zenodo.21338004

## Files to Upload

These are the files uploaded to the published Zenodo record:

- `demand-forecasting-technical-report-v1.pdf` - final technical-report PDF.
- `paper-source-v1.zip` - LaTeX source, bibliography, class/style files, and
  paper figures needed to rebuild the PDF.
- `replication-materials-v1.zip` - extraction table, analysis scripts,
  generated analysis outputs, benchmark code, exported result tables, tests,
  and reproduction notes.

Optional supporting files:

- `zenodo_form_fields.md` - metadata to paste into the Zenodo web form.
- `zenodo_metadata.json` - API-style metadata draft.
- `CITATION.cff` - citation metadata with the assigned DOI.
- `LICENSE-REPORT.md` - recommended license notice for the report record.
- `SHA256SUMS.txt` - checksums for the three upload files.

## Safety Notes

This release package intentionally excludes:

- the contract PDF uploaded for private review,
- raw competition datasets,
- local MLflow stores,
- local logs,
- local cache directories,
- downloaded model checkpoints.

Raw datasets remain available only from their original providers. The release
contains derived extraction/result tables and code needed to regenerate the
reported analysis outputs.

## Published Record

The v1.0 record is published at
<https://doi.org/10.5281/zenodo.21338004>.

Do not overwrite the three upload files in this directory if you need to keep a
local snapshot matching the published Zenodo record. For corrections, create a
new Zenodo version and stage it in a new release directory.
