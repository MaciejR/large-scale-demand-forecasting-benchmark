# Publication Handoff: v1.12

This is the operational checklist for publishing the current v1.12 repair
package.  The repository is now public; the GitHub release and asset must stay
synchronized with the source commit recorded inside the package.

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

Expected state before touching the public release:

- `pytest` passes.
- `tools/build_v112_release.sh` passes privacy, manifest, provenance, checksum,
  zip-integrity, manuscript, PRISMA, citation, Source B, and meta-regression
  gates.
- `python3 tools/audit_publication_readiness.py` passes.
- `python3 tools/audit_publication_readiness.py --require-public` passes after
  the GitHub release asset has been updated for the current package.

## GitHub Release State

The public GitHub repository and v1.12 release are part of the publication
state.  After every commit that changes packaged content, rebuild the package,
replace the GitHub release asset, and rerun:

```bash
python3 tools/audit_publication_readiness.py --require-public
python3 tools/audit_zenodo_upload_readiness.py
python3 tools/audit_publication_log_v112.py
```

The public-ready state is reached only when all three commands pass.  The
public-readiness audit includes the GitHub release download-verification gate.

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
python3 tools/audit_zenodo_upload_readiness.py --require-token
```

The root `.zenodo.json` is intentionally kept equivalent as JSON data to
`docs/ZENODO_METADATA_V1.12.json`; the metadata audit fails if they diverge.
Token variable names are documented in `.env.example`; keep real values only in
local `.env`, which is ignored and excluded from release packages.  The
`tools/publish_v112_zenodo.sh` wrapper imports only the known Zenodo token
variables from `.env` when they are not already set; direct `python3
tools/zenodo_upload_v112.py ...` calls require the token variables to be present
in the shell environment.

Before uploading, verify package provenance:

```bash
cat release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair/COMMIT.txt
git rev-parse HEAD
shasum -a 256 release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip
```

The first two hashes must match.  The uploader records the outer ZIP checksum
in the Zenodo notes at upload time; do not write that checksum into tracked
files inside the package.

The scripted upload path is:

```bash
python3 tools/zenodo_upload_v112.py --dry-run
python3 tools/zenodo_upload_v112.py
```

The wrapper path is:

```bash
tools/publish_v112_zenodo.sh dry-run
tools/publish_v112_zenodo.sh draft --output-json /tmp/zenodo-v1.12-draft.json
# or update an existing unpublished draft:
tools/publish_v112_zenodo.sh draft --deposition-id <draft-id> --output-json /tmp/zenodo-v1.12-draft.json
```

The wrapper does not modify tracked files.  Inspect the draft JSON before
deciding whether to update the publication log, commit a draft note, or proceed
to publication.  The wrapper relies on
`python3 tools/audit_publication_readiness.py --require-public` for the GitHub
release download-verification gate, so it does not run a second asset download.
`tools/publish_v112_zenodo.sh` and
`python3 tools/audit_zenodo_upload_readiness.py --require-token` both read a
local ignored `.env` file when present, but only import known Zenodo token
variables and never override values already exported in the process environment.

For a non-archival sandbox check, use a separate sandbox token:

```bash
python3 tools/audit_zenodo_upload_readiness.py --require-token --sandbox-token
python3 tools/zenodo_upload_v112.py --sandbox
tools/publish_v112_zenodo.sh sandbox-draft --output-json /tmp/zenodo-v1.12-sandbox.json
```

This creates or updates an unpublished Zenodo draft and uploads the audited
package plus metadata.  The uploader appends the outer ZIP SHA-256 to the
Zenodo record notes at upload time; this avoids storing a circular checksum in
the metadata file packaged inside the ZIP.  Publishing is a separate
irreversible step:

```bash
tools/publish_v112_zenodo.sh publish --deposition-id <draft-id> --output-json /tmp/zenodo-v1.12-publish.json
python3 tools/update_publication_log_v112.py --zenodo-json /tmp/zenodo-v1.12-publish.json --apply
```

This first publication-log update records the exact GitHub release target and
asset SHA-256 that were uploaded to Zenodo.  Those fields intentionally remain
the Zenodo-uploaded package identity after the later DOI metadata commits.

## After Zenodo Minting

After a v1.12 DOI is minted, update:

- `README.md`
- `CITATION.cff`
- `paper/latex/main.tex`
- `docs/RELEASE_V1.12.md`

Use the scripted DOI update path:

```bash
python3 tools/apply_v112_zenodo_doi.py --doi 10.5281/zenodo.<new-record-id>
python3 tools/apply_v112_zenodo_doi.py --doi 10.5281/zenodo.<new-record-id> --apply
```

Then verify the metadata edits before committing:

```bash
pytest
git diff --check
```

Commit and push the DOI metadata update.  The release builder requires a clean
tree because `COMMIT.txt` must identify a real commit.  After the DOI metadata
commit is pushed, rebuild the package, replace the GitHub release asset, and
verify the public release state:

```bash
tools/build_v112_release.sh
gh release edit v1.12 --target "$(git rev-parse HEAD)"
gh release upload v1.12 release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip --clobber
python3 tools/audit_publication_readiness.py --require-public
```

Then record the full DOI metadata commit SHA in the publication log.  The
publish JSON includes `published_at_utc`, which the helper copies into the
`Published at` field; this second log update preserves the already-recorded
Zenodo-uploaded target commit and asset SHA:

```bash
python3 tools/update_publication_log_v112.py \
  --zenodo-json /tmp/zenodo-v1.12-publish.json \
  --doi-update-commit "$(git rev-parse HEAD)" \
  --apply
```

Commit and push the publication-log update, then rebuild the final package once
more so `COMMIT.txt`, `CHECKSUMS.txt`, and citation metadata agree.  Replace the
GitHub release asset again before the public-readiness audit.  Do not write the
outer ZIP checksum into a tracked file inside the package; the public-readiness
audit verifies the final GitHub release target and downloaded asset digest.  You
can also run the GitHub release gate directly with:

```bash
tools/build_v112_release.sh
gh release edit v1.12 --target "$(git rev-parse HEAD)"
gh release upload v1.12 release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip --clobber
python3 tools/audit_publication_readiness.py --require-public
python3 tools/audit_github_release.py --verify-download
```

Finally verify that the Zenodo DOI fields in `docs/PUBLICATION_LOG_V1.12.md`
include the production DOI, DOI URL, Zenodo record URL, ISO-8601 UTC
`Published at` timestamp, and full 40-character `DOI metadata update commit`:

```bash
python3 tools/audit_publication_log_v112.py --require-complete
python3 tools/audit_publication_readiness.py --require-public --require-complete-log
```
