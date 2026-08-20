#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -z "${IJF_POSTAL_ADDRESS:-}" ]]; then
  echo "Set IJF_POSTAL_ADDRESS before building the private submission bundle" >&2
  exit 1
fi

anon_zip="release/v1.21/v1.21-ijf-anonymous-supplement.zip"
if [[ ! -f "$anon_zip" ]]; then
  echo "Build v1.21 release packages first: tools/build_v121_release.sh" >&2
  exit 1
fi
python3 tools/audit_v121_release.py

SKIP_PRIVATE_TITLE_PAGE=0 tools/build_ijf_submission_files.sh
release_manuscript="release/v1.21/v1.21-ijf-submission-ready/manuscript/manuscript-double-anonymized-v1.21.pdf"
if ! cmp -s paper/latex/main_anonymized.pdf "$release_manuscript"; then
  echo "Current anonymous manuscript differs from the immutable v1.21 release" >&2
  exit 1
fi
private_dir="release/private-ijf-submission/v1.21"
stage_dir="$(mktemp -d "release/.private-ijf-stage-XXXXXX")"
trap 'rm -rf "$stage_dir"' EXIT

cp paper/latex/main_anonymized.pdf "$stage_dir/manuscript-anonymized.pdf"
cp paper/submission/title_page.pdf "$stage_dir/title-page-private.pdf"
cp paper/submission/cover_letter.pdf "$stage_dir/cover-letter.pdf"
cp paper/submission/highlights.txt "$stage_dir/highlights.txt"
cp paper/submission/declaration_of_interests.docx \
  "$stage_dir/declaration-of-interests.docx"
cp "$anon_zip" "$stage_dir/anonymous-replication-supplement.zip"

if pdftotext "$stage_dir/title-page-private.pdf" - | \
  grep -Fq '[complete postal address required before submission]'; then
  echo "Private title page still contains the postal-address placeholder" >&2
  exit 1
fi
python3 tools/audit_ijf_anonymity.py "$stage_dir/manuscript-anonymized.pdf"
python3 tools/audit_ijf_declaration.py "$stage_dir/declaration-of-interests.docx"

(
  cd "$stage_dir"
  find . -type f ! -name 'CHECKSUMS.txt' -print0 | sort -z | \
    xargs -0 shasum -a 256 > CHECKSUMS.txt
)

mkdir -p "$(dirname "$private_dir")"
if [[ -e "$private_dir" ]]; then
  if diff -qr "$stage_dir" "$private_dir" >/dev/null; then
    echo "Existing private IJF bundle is identical; leaving it unchanged"
    exit 0
  fi
  echo "Refusing to replace existing private IJF bundle: $private_dir" >&2
  exit 1
fi
mv "$stage_dir" "$private_dir"
trap - EXIT
echo "Built private IJF submission bundle: $private_dir"
