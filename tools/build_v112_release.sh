#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

release_dir="release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair"
zip_path="${release_dir}.zip"
pdf_name="demand-forecasting-timesfm-fev-bench-wape-covariance-repair-v1.12.pdf"

if [[ "${ALLOW_DIRTY_RELEASE:-0}" != "1" ]]; then
  dirty_status="$(git status --porcelain --untracked-files=all)"
  if [[ -n "$dirty_status" ]]; then
    echo "Refusing to build a release from a dirty working tree:" >&2
    echo "$dirty_status" >&2
    echo "Commit or remove these changes, or set ALLOW_DIRTY_RELEASE=1 for local debugging only." >&2
    exit 1
  fi
fi

rm -rf "$release_dir" "$zip_path"
mkdir -p "$release_dir/manuscript" "$release_dir/replication"

python3 tools/audit_citations.py
python3 tools/audit_prisma_counts.py
python3 analysis/prisma_flow_diagram.py >/tmp/v112_prisma_flow.log
prisma_status="$(git status --porcelain -- analysis/figures/prisma_flow.pdf analysis/figures/prisma_flow.png)"
if [[ -n "$prisma_status" ]]; then
  echo "PRISMA flow diagram changed during release build:" >&2
  echo "$prisma_status" >&2
  echo "Review and commit regenerated PRISMA figures before packaging." >&2
  exit 1
fi

tools/audit_manuscript_v112.sh
Rscript analysis/meta_regression.R >/tmp/v112_meta_regression.log
meta_status="$(
  git status --porcelain -- \
    analysis/figures \
    analysis/study_characteristics.csv \
    analysis/risk_of_bias_assessment.csv
)"
if [[ -n "$meta_status" ]]; then
  echo "Meta-regression artifacts changed during release build:" >&2
  echo "$meta_status" >&2
  echo "Review and commit regenerated analysis artifacts before packaging." >&2
  exit 1
fi

python3 analysis/source_b_integrity_audit.py >/tmp/v112_source_b_integrity_audit.log
source_b_status="$(git status --porcelain -- analysis/figures)"
if [[ -n "$source_b_status" ]]; then
  echo "Source B audit artifacts changed during release build:" >&2
  echo "$source_b_status" >&2
  echo "Review and commit regenerated analysis/figures artifacts before packaging." >&2
  exit 1
fi

tools/build_manuscript_pdf.sh
pdf_status="$(git status --porcelain -- paper/latex/main.pdf)"
if [[ -n "$pdf_status" ]]; then
  echo "Manuscript PDF changed during release build:" >&2
  echo "$pdf_status" >&2
  echo "Review and commit the rebuilt paper/latex/main.pdf before packaging." >&2
  exit 1
fi

git rev-parse HEAD > "$release_dir/COMMIT.txt"
cp paper/latex/main.pdf "$release_dir/manuscript/$pdf_name"

rsync -a ./ "$release_dir/replication/" \
  --exclude '.git/' \
  --exclude '.claude/' \
  --exclude 'release/' \
  --exclude 'data/raw/' \
  --exclude 'mlruns/' \
  --exclude 'logs/' \
  --exclude '.env' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '*.pyc' \
  --exclude '*.log' \
  --exclude '*.ckpt' \
  --exclude '*.pt' \
  --exclude '*.pth' \
  --exclude '*.safetensors' \
  --exclude 'analysis/baseline_results.md' \
  --exclude 'paper/drafts/' \
  --exclude 'paper/latex/*.aux' \
  --exclude 'paper/latex/*.bbl' \
  --exclude 'paper/latex/*.blg' \
  --exclude 'paper/latex/*.out' \
  --exclude 'paper/latex/*.spl' \
  --exclude 'paper/latex/*.synctex.gz' \
  --exclude 'benchmark/results/fev_bench_official/' \
  --exclude '*/source_b_v1_11_timesfm25_m5_rohlik_100_batched/' \
  --exclude 'Umowa*.pdf'

cp "$release_dir/replication/docs/RELEASE_V1.12.md" "$release_dir/README.md"

(cd "$release_dir" && \
  find . -type f ! -name 'CHECKSUMS.txt' -print0 | sort -z | \
  xargs -0 shasum -a 256 > CHECKSUMS.txt)

(cd release && zip -qr "$(basename "$zip_path")" "$(basename "$release_dir")")

head_sha="$(git rev-parse HEAD)"
package_sha="$(cat "$release_dir/COMMIT.txt")"
if [[ "$head_sha" != "$package_sha" ]]; then
  echo "COMMIT.txt mismatch: package=$package_sha head=$head_sha" >&2
  exit 1
fi

(cd "$release_dir" && shasum -a 256 -c CHECKSUMS.txt >/tmp/v112_release_checksums.log)
unzip -t "$zip_path" >/tmp/v112_release_zip.log

privacy_hits="$(
  find "$release_dir" \( \
    -path '*data/raw*' \
    -o -path '*mlruns*' \
    -o -path '*logs*' \
    -o -path '*/.pytest_cache*' \
    -o -name '__pycache__' \
    -o -name 'Umowa*.pdf' \
    -o -name '.env' \
    -o -name '.DS_Store' \
    -o -name '*.pyc' \
    -o -name '*.log' \
    -o -name '*.ckpt' \
    -o -name '*.pt' \
    -o -name '*.pth' \
    -o -name '*.safetensors' \
    -o -path '*benchmark/results/fev_bench_official*' \
    -o -path '*source_b_v1_11_timesfm25_m5_rohlik_100_batched*' \
  \) -print | sort
)"

if [[ -n "$privacy_hits" ]]; then
  echo "Release package contains excluded files:" >&2
  echo "$privacy_hits" >&2
  exit 1
fi

python3 tools/audit_release_privacy.py "$release_dir"
python3 tools/audit_release_manifest.py "$release_dir"
python3 tools/audit_release_provenance.py "$release_dir"
python3 tools/audit_zenodo_metadata.py

du -sh "$zip_path" "$release_dir"
echo "Built and audited $zip_path at $head_sha"
