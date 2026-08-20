#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

release_root="release/v1.21"
public_stem="v1.21-ijf-submission-ready"
anon_stem="v1.21-ijf-anonymous-supplement"

if [[ "${ALLOW_DIRTY_RELEASE:-0}" != "1" ]]; then
  dirty_status="$(git status --porcelain --untracked-files=all)"
  if [[ -n "$dirty_status" ]]; then
    echo "Refusing to build a release from a dirty working tree:" >&2
    echo "$dirty_status" >&2
    exit 1
  fi
fi

head_sha="$(git rev-parse HEAD)"
SKIP_PRIVATE_TITLE_PAGE=1 tools/build_ijf_submission_files.sh
python3 tools/audit_ijf_declaration.py paper/submission/declaration_of_interests.docx
python3 tools/validate_m5_200trial_artifact.py
tools/audit_manuscript_v112.sh
pytest -q
git diff --check

generated_status="$(git status --porcelain -- paper/latex/main.pdf paper/latex/main_anonymized.pdf analysis benchmark/results)"
if [[ -n "$generated_status" ]]; then
  echo "Tracked scientific/manuscript artifacts changed during build:" >&2
  echo "$generated_status" >&2
  exit 1
fi

mkdir -p release
stage_root="$(mktemp -d "release/.v121-stage-XXXXXX")"
trap 'rm -rf "$stage_root"' EXIT
source_tree="$stage_root/source"
publish_stage="$stage_root/v1.21"
public_stage="$publish_stage/$public_stem"
anon_stage="$publish_stage/$anon_stem"
public_zip_stage="$publish_stage/$public_stem.zip"
anon_zip_stage="$publish_stage/$anon_stem.zip"
mkdir -p "$source_tree" "$public_stage/manuscript" "$public_stage/submission" \
  "$public_stage/replication" "$anon_stage"

git archive --format=tar HEAD | tar -xf - -C "$source_tree"

printf '%s\n' "$head_sha" > "$public_stage/COMMIT.txt"
cp paper/latex/main.pdf "$public_stage/manuscript/manuscript-public-v1.21.pdf"
cp paper/latex/main_anonymized.pdf \
  "$public_stage/manuscript/manuscript-double-anonymized-v1.21.pdf"
cp paper/submission/cover_letter.md paper/submission/cover_letter.pdf \
  paper/submission/highlights.txt paper/submission/declaration_of_interests.docx \
  paper/submission/title_page.tex "$public_stage/submission/"
cp docs/IJF_SUBMISSION_CHECKLIST.md docs/IJF_SUBMISSION_LOG.md \
  docs/RELEASE_V1.21.md "$public_stage/submission/"
cp docs/RELEASE_V1.21.md "$public_stage/README.md"

rsync -a "$source_tree/" "$public_stage/replication/" \
  --exclude '.zenodo.json' \
  --exclude 'data/raw/' \
  --exclude 'analysis/baseline_results.md' \
  --exclude 'paper/drafts/' \
  --exclude 'paper/latex/*.aux' \
  --exclude 'paper/latex/*.bbl' \
  --exclude 'paper/latex/*.blg' \
  --exclude 'paper/latex/*.out' \
  --exclude 'paper/latex/*.spl' \
  --exclude 'paper/latex/*.synctex.gz' \
  --exclude 'paper/submission/title_page.pdf' \
  --exclude 'benchmark/results/fev_bench_official/' \
  --exclude 'benchmark/results/source_b_paired_panel/source_b_v1_15_strong_lightgbm_200trial_top_volume_100/' \
  --exclude 'benchmark/results/source_b_paired_panel/source_b_v1_11_timesfm25_m5_rohlik_100_batched/' \
  --exclude 'Umowa*.pdf'

cp paper/submission/anonymous_supplement_readme.md "$anon_stage/README.md"
printf '%s\n' 'Peer-review snapshot v1.21; public commit withheld for double-anonymized review.' \
  > "$anon_stage/SOURCE_STATE.txt"
cp "$source_tree/ARTIFACTS.md" "$anon_stage/"
cp paper/submission/anonymous_supplement_reproducing.md \
  "$anon_stage/REPRODUCING.md"
rsync -a "$source_tree/analysis/" "$anon_stage/analysis/" \
  --exclude 'baseline_results.md'
rsync -a "$source_tree/benchmark/code/" "$anon_stage/benchmark/code/"
rsync -a "$source_tree/benchmark/results/" "$anon_stage/benchmark/results/" \
  --exclude 'fev_bench_official/' \
  --exclude 'source_b_paired_panel/source_b_v1_15_strong_lightgbm_200trial_top_volume_100/' \
  --exclude 'source_b_paired_panel/source_b_v1_11_timesfm25_m5_rohlik_100_batched/'
mkdir -p "$anon_stage/data"
rsync -a "$source_tree/data/m5_200trial/" "$anon_stage/data/m5_200trial/"
mkdir -p "$anon_stage/tools"
cp "$source_tree/tools/export_mlflow_to_csv.py" \
  "$source_tree/tools/validate_m5_200trial_artifact.py" \
  "$source_tree/tools/run_strong_lightgbm_challenge_shards.sh" \
  "$anon_stage/tools/"

python3 tools/anonymize_ijf_supplement.py "$anon_stage" --sanitize

for package_dir in "$public_stage" "$anon_stage"; do
  (
    cd "$package_dir"
    find . -type f ! -name 'CHECKSUMS.txt' -print0 | sort -z | \
      xargs -0 shasum -a 256 > CHECKSUMS.txt
    shasum -a 256 -c CHECKSUMS.txt >/dev/null
  )
done

python3 tools/create_deterministic_zip.py "$public_stage" "$public_zip_stage"
python3 tools/create_deterministic_zip.py "$anon_stage" "$anon_zip_stage"
unzip -t "$public_zip_stage" >/dev/null
unzip -t "$anon_zip_stage" >/dev/null
python3 tools/audit_v121_release.py \
  --public-dir "$public_stage" \
  --anon-dir "$anon_stage" \
  --expected-head "$head_sha" \
  --public-zip "$public_zip_stage" \
  --anon-zip "$anon_zip_stage"

if [[ -e "$release_root" ]]; then
  existing_public="$release_root/$public_stem.zip"
  existing_anon="$release_root/$anon_stem.zip"
  if [[ ! -f "$existing_public" || ! -f "$existing_anon" ]] || \
    [[ "$(shasum -a 256 "$existing_public" | awk '{print $1}')" != \
       "$(shasum -a 256 "$public_zip_stage" | awk '{print $1}')" ]] || \
    [[ "$(shasum -a 256 "$existing_anon" | awk '{print $1}')" != \
       "$(shasum -a 256 "$anon_zip_stage" | awk '{print $1}')" ]]; then
    echo "Refusing to replace existing immutable release: $release_root" >&2
    exit 1
  fi
  echo "Existing v1.21 release is byte-identical; leaving it unchanged"
else
  mv "$publish_stage" "$release_root"
fi

python3 tools/audit_v121_release.py
du -sh "$release_root/$public_stem.zip" "$release_root/$anon_stem.zip"
echo "Built and audited v1.21 release packages at $head_sha"
