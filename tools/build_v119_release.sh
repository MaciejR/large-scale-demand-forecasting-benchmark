#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

release_dir="release/zenodo-v1.19-ijf-submission-prep"
zip_path="${release_dir}.zip"
pdf_name="demand-forecasting-ijf-submission-prep-v1.19.pdf"

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

python3 analysis/prisma_flow_diagram.py >/tmp/v119_structured_flow.log
flow_status="$(git status --porcelain -- analysis/figures/prisma_flow.pdf analysis/figures/prisma_flow.png)"
if [[ -n "$flow_status" ]]; then
  echo "Structured-search flow diagram changed during release build:" >&2
  echo "$flow_status" >&2
  echo "Review and commit regenerated flow figures before packaging." >&2
  exit 1
fi

python3 tools/validate_m5_200trial_artifact.py
python3 analysis/source_b_paired_panel_report.py --runs \
  source_b_repair_baselines_favorita_100_v1_5 \
  source_b_repair_baselines_m5_rohlik_100_v2 \
  source_b_repair_fm_chronos2_favorita_100_v1_5 \
  source_b_repair_fm_chronos2_m5_rohlik_100 \
  source_b_repair_fm_chronos_bolt_favorita_100_v1_5 \
  source_b_repair_fm_chronos_bolt_m5_rohlik_100 \
  source_b_repair_fm_moirai2_favorita_100_v1_5 \
  source_b_repair_fm_moirai2_m5_rohlik_100 \
  source_b_repair_fm_timesfm25_favorita_100_v1_5 \
  source_b_v1_11_timesfm25_m5_rohlik_100_batched \
  source_b_v1_13_tuned_lightgbm_cov_100 \
  source_b_v1_13_tuned_lightgbm_direct_100 \
  source_b_v1_6_tirex_batched_favorita_100 \
  source_b_v1_7_tirex_batched_m5_rohlik_100 \
  source_b_v1_19_m5_rich_lightgbm_100 \
  --n-bootstrap 1000 >/tmp/v119_source_b_report.log
python3 analysis/source_b_m5_200trial_sensitivity.py --n-bootstrap 1000 >/tmp/v119_m5_200trial.log
python3 analysis/source_b_m5_panel_scaled_metric.py >/tmp/v119_m5_panel_scaled.log
python3 analysis/source_b_prespecified_baseline_sensitivity.py >/tmp/v119_prespecified_baseline.log

m5_status="$(
  git status --porcelain -- \
    data/m5_200trial \
    analysis/figures/source_b_paired_panel_bootstrap_draws.csv \
    analysis/figures/source_b_paired_panel_cell_summary.csv \
    analysis/figures/source_b_paired_panel_fm_vs_best_baseline.csv \
    analysis/figures/source_b_paired_panel_lightgbm_tuning_trials.csv \
    analysis/figures/source_b_paired_panel_logratio_covariance.csv \
    analysis/figures/source_b_paired_panel_logratio_covariance_long.csv \
    analysis/figures/source_b_paired_panel_per_series_metrics.csv \
    analysis/figures/source_b_paired_panel_run_ledger.csv \
    analysis/figures/source_b_m5_200trial_best_baselines.csv \
    analysis/figures/source_b_m5_200trial_fm_vs_best_high_budget_baseline.csv \
    analysis/figures/source_b_m5_panel_scaled_metric.csv \
    analysis/figures/source_b_m5_panel_scaled_metric_contrasts.csv \
    analysis/figures/source_b_m5_panel_scaled_metric_chronos2.tex \
    analysis/figures/source_b_prespecified_lightgbm_tuned_cov_contrasts.csv \
    analysis/figures/source_b_prespecified_lightgbm_tuned_cov_chronos2.tex
)"
if [[ -n "$m5_status" ]]; then
  echo "M5 sensitivity artifacts changed during release build:" >&2
  echo "$m5_status" >&2
  echo "Review and commit regenerated M5 sensitivity artifacts before packaging." >&2
  exit 1
fi

tools/build_manuscript_pdf.sh
tools/audit_manuscript_v112.sh

if pdftotext paper/latex/main.pdf - | grep -E "PRISMA-Informed|Systematic Review:|Supplemental Heuristic-Weight Diagnostics|Task-clustered CR2|rma\\.mv" >/tmp/v119_forbidden_pdf_terms.log; then
  echo "Manuscript PDF still contains removed review-risk terms:" >&2
  cat /tmp/v119_forbidden_pdf_terms.log >&2
  exit 1
fi

if ! pdftotext paper/latex/main.pdf - | grep -F "GitHub release v1.19" >/tmp/v119_required_pdf_terms.log; then
  echo "Manuscript PDF does not contain GitHub release v1.19 data-availability text." >&2
  exit 1
fi

pdf_status="$(git status --porcelain -- paper/latex/main.pdf)"
if [[ -n "$pdf_status" ]]; then
  echo "Manuscript PDF changed during release build:" >&2
  echo "$pdf_status" >&2
  echo "Review and commit the rebuilt paper/latex/main.pdf before packaging." >&2
  exit 1
fi

pytest >/tmp/v119_pytest.log
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

cp docs/RELEASE_V1.19.md "$release_dir/README.md"

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

(cd "$release_dir" && shasum -a 256 -c CHECKSUMS.txt >/tmp/v119_release_checksums.log)
unzip -t "$zip_path" >/tmp/v119_release_zip.log

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
  "$release_dir/replication/analysis/source_b_m5_200trial_sensitivity.py"
  "$release_dir/replication/analysis/source_b_m5_panel_scaled_metric.py"
  "$release_dir/replication/analysis/source_b_prespecified_baseline_sensitivity.py"
  "$release_dir/replication/analysis/figures/source_b_m5_panel_scaled_metric.csv"
  "$release_dir/replication/analysis/figures/source_b_m5_panel_scaled_metric_contrasts.csv"
  "$release_dir/replication/analysis/figures/source_b_m5_panel_scaled_metric_chronos2.tex"
  "$release_dir/replication/analysis/figures/source_b_prespecified_lightgbm_tuned_cov_contrasts.csv"
  "$release_dir/replication/analysis/figures/source_b_prespecified_lightgbm_tuned_cov_chronos2.tex"
  "$release_dir/replication/analysis/figures/prisma_flow.pdf"
  "$release_dir/replication/benchmark/results/source_b_paired_panel/source_b_v1_19_m5_rich_lightgbm_100/cell_summary.csv"
  "$release_dir/replication/benchmark/results/source_b_paired_panel/source_b_v1_19_m5_rich_lightgbm_100/predictions_all.parquet"
  "$release_dir/replication/tools/build_v119_release.sh"
  "$release_dir/replication/docs/RELEASE_V1.19.md"
)
for path in "${required_files[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "Missing required release file: $path" >&2
    exit 1
  fi
done

du -sh "$zip_path" "$release_dir"
echo "Built and audited $zip_path at $head_sha"
