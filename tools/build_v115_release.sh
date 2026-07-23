#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

release_dir="release/zenodo-v1.15-m5-200trial-lightgbm-sensitivity"
zip_path="${release_dir}.zip"
pdf_name="demand-forecasting-m5-200trial-lightgbm-sensitivity-v1.15.pdf"

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

python3 tools/validate_m5_200trial_artifact.py
python3 analysis/source_b_m5_200trial_sensitivity.py --n-bootstrap 1000 >/tmp/v115_m5_200trial.log

m5_status="$(
  git status --porcelain -- \
    data/m5_200trial \
    analysis/figures/source_b_m5_200trial_best_baselines.csv \
    analysis/figures/source_b_m5_200trial_fm_vs_best_high_budget_baseline.csv
)"
if [[ -n "$m5_status" ]]; then
  echo "M5 200-trial artifacts changed during release build:" >&2
  echo "$m5_status" >&2
  echo "Review and commit regenerated M5 200-trial artifacts before packaging." >&2
  exit 1
fi

tools/build_manuscript_pdf.sh
tools/audit_manuscript_v112.sh

pdf_status="$(git status --porcelain -- paper/latex/main.pdf)"
if [[ -n "$pdf_status" ]]; then
  echo "Manuscript PDF changed during release build:" >&2
  echo "$pdf_status" >&2
  echo "Review and commit the rebuilt paper/latex/main.pdf before packaging." >&2
  exit 1
fi

pytest >/tmp/v115_pytest.log
git diff --check

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
  --exclude 'benchmark/results/source_b_paired_panel/_quarantine/' \
  --exclude 'benchmark/results/source_b_paired_panel/source_b_v1_15_strong_lightgbm_200trial_top_volume_100/' \
  --exclude '*/source_b_v1_11_timesfm25_m5_rohlik_100_batched/' \
  --exclude 'Umowa*.pdf'

cp docs/RELEASE_V1.15.md "$release_dir/README.md"

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

(cd "$release_dir" && shasum -a 256 -c CHECKSUMS.txt >/tmp/v115_release_checksums.log)
unzip -t "$zip_path" >/tmp/v115_release_zip.log

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
    -o -path '*source_b_v1_15_strong_lightgbm_200trial_top_volume_100*' \
    -o -path '*source_b_v1_11_timesfm25_m5_rohlik_100_batched*' \
  \) -print | sort
)"

if [[ -n "$privacy_hits" ]]; then
  echo "Release package contains excluded files:" >&2
  echo "$privacy_hits" >&2
  exit 1
fi

python3 tools/audit_release_privacy.py "$release_dir"

required_files=(
  "$release_dir/COMMIT.txt"
  "$release_dir/CHECKSUMS.txt"
  "$release_dir/README.md"
  "$release_dir/manuscript/$pdf_name"
  "$release_dir/replication/data/m5_200trial/artifact_manifest.json"
  "$release_dir/replication/data/m5_200trial/m5_lightgbm_200trial_fm_vs_best_high_budget_baseline.csv"
  "$release_dir/replication/analysis/source_b_m5_200trial_sensitivity.py"
  "$release_dir/replication/tools/validate_m5_200trial_artifact.py"
  "$release_dir/replication/tests/test_m5_200trial_sensitivity.py"
  "$release_dir/replication/docs/RELEASE_V1.15.md"
)
for path in "${required_files[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "Missing required release file: $path" >&2
    exit 1
  fi
done

for run_dir in \
  source_b_v1_15_m5_h7_lightgbm_tuned_cov_200trial \
  source_b_v1_15_m5_h14_lightgbm_tuned_cov_200trial \
  source_b_v1_15_m5_h28_lightgbm_tuned_cov_200trial \
  source_b_v1_15_m5_h7_lightgbm_tuned_direct_200trial \
  source_b_v1_15_m5_h14_lightgbm_tuned_direct_200trial \
  source_b_v1_15_m5_h28_lightgbm_tuned_direct_200trial; do
  if [[ ! -f "$release_dir/replication/benchmark/results/source_b_paired_panel/$run_dir/cell_summary.csv" ]]; then
    echo "Missing packaged 200-trial run summary: $run_dir" >&2
    exit 1
  fi
done

du -sh "$zip_path" "$release_dir"
echo "Built and audited $zip_path at $head_sha"
