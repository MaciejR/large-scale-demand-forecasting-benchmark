# Release Notes: v1.21 IJF Submission-Ready Package

Release commit: recorded in the release package `COMMIT.txt`.

Local package target: `release/v1.21/v1.21-ijf-submission-ready.zip`.

## Summary

Version v1.21 freezes the v1.20 scientific evidence base and repairs the final
submission layer for the International Journal of Forecasting. It adds a
double-anonymized manuscript, journal-facing submission documents, an abstract
within the journal's 100--150-word limit, an explicit generative-AI declaration,
and stricter release exclusions for caches and local metadata.

## Submission files

- Public manuscript PDF and LaTeX source.
- Double-anonymized manuscript PDF and LaTeX source.
- Separate title-page source template; the private PDF is built locally from
  the uncommitted `IJF_POSTAL_ADDRESS` environment variable.
- Cover letter PDF/source and highlights.
- Elsevier declaration-of-interests DOCX.
- IJF checklist and submission tracking log.
- An anonymized replication supplement for peer review.

## Scientific scope

The analyses, estimates, tables, and figures are unchanged from v1.20. Further
model families or covariance extensions are deferred unless requested during
peer review.

## Privacy and integrity

The package excludes raw data, MLflow stores, logs, model checkpoints, local
caches, `.zenodo.json`, private files, and full untracked prediction trees.
Every packaged file is covered by `CHECKSUMS.txt`. The public package records
the exact source state in `COMMIT.txt`; the anonymous reviewer supplement
intentionally withholds the searchable Git commit and contains a non-identifying
`SOURCE_STATE.txt` marker instead. ZIP creation uses fixed timestamps and sorted
paths for byte-reproducible archives.
