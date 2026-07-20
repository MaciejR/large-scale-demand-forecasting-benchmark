# Publication Handoff: v1.12

This is the operational checklist for publishing the current v1.12 repair
package.  It assumes the repository remains private until the final visibility
step.

## Current Package

- Branch: `v1.7-tirex-m5-rohlik`
- Package: `release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip`
- Manuscript PDF inside package:
  `manuscript/demand-forecasting-timesfm-fev-bench-wape-covariance-repair-v1.12.pdf`
- Source commit: recorded in `release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair/COMMIT.txt`

## Pre-Publication Checks

Run from the repository root:

```bash
pytest
git diff --check
tools/build_v112_release.sh
python3 tools/audit_publication_readiness.py
python3 tools/audit_zenodo_metadata.py
```

Expected state before changing visibility:

- `pytest` passes.
- `tools/build_v112_release.sh` passes privacy, manifest, provenance, checksum,
  zip-integrity, manuscript, PRISMA, citation, Source B, and meta-regression
  gates.
- `python3 tools/audit_publication_readiness.py` passes.
- `python3 tools/audit_publication_readiness.py --require-public` fails only
  because GitHub visibility is still `PRIVATE`.

## GitHub Visibility Step

After the package audit passes, make the repository public in GitHub settings
or with:

```bash
gh repo edit MaciejR/large-scale-demand-forecasting-benchmark --visibility public
```

Then rerun:

```bash
python3 tools/audit_publication_readiness.py --require-public
python3 tools/audit_github_release.py
```

The public-ready state is reached only when both commands pass.

## Zenodo Upload

Upload the audited zip file:

```text
release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip
```

Use the release notes in `docs/RELEASE_V1.12.md` as the description.  Keep the
historical v1.0 DOI unchanged; publish v1.12 as a separate repair package or as
a new version only if that is the intended archival policy.
Use `docs/ZENODO_METADATA_V1.12.json` as the metadata draft and verify it with:

```bash
python3 tools/audit_zenodo_metadata.py
```

Before uploading, verify package provenance:

```bash
cat release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair/COMMIT.txt
git rev-parse HEAD
shasum -a 256 release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip
```

The first two hashes must match.  Record the zip checksum in the Zenodo notes
or local publication log if Zenodo does not expose it directly.

## After Zenodo Minting

After a v1.12 DOI is minted, update:

- `README.md`
- `CITATION.cff`
- `paper/latex/main.tex`
- `docs/RELEASE_V1.12.md`

Then rerun:

```bash
pytest
tools/build_v112_release.sh
python3 tools/audit_publication_readiness.py --require-public
```

Commit and push the DOI metadata update, then rebuild the final package once
more so `COMMIT.txt`, `CHECKSUMS.txt`, and citation metadata agree.
