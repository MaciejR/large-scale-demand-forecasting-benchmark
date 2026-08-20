# Reproducing the Anonymous Supplement Checks

Run these commands from the unpacked supplement root.

Verify every packaged file against the archive manifest:

```bash
shasum -a 256 -c CHECKSUMS.txt
```

Validate the allow-listed six-run M5 200-trial LightGBM sensitivity artifact:

```bash
python3 tools/validate_m5_200trial_artifact.py
```

The validator requires Python 3 with NumPy, pandas, and PyArrow. Raw competition
datasets are intentionally excluded. The packaged derived tables, per-series
metrics, tuning ledgers, predictions, manifests, and analysis source are enough
for this validation and for auditing the reported 200-trial sensitivity.

The full environment specification and raw-data reconstruction workflow are
withheld from this anonymous snapshot where they would expose the public
repository. They will be restored after double-anonymized review.
