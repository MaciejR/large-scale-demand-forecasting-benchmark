#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  tools/publish_v112_zenodo.sh dry-run
  tools/publish_v112_zenodo.sh draft [--output-json PATH]
  tools/publish_v112_zenodo.sh sandbox-draft [--output-json PATH]
  tools/publish_v112_zenodo.sh publish --deposition-id ID [--output-json PATH]

Runs the required v1.12 publication audits before calling the Zenodo uploader.
The publish action is irreversible on Zenodo and therefore requires an explicit
deposition ID.
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi

action="$1"
shift
deposition_id=""
output_json="/tmp/zenodo-v1.12-${action}.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --deposition-id)
      if [[ $# -lt 2 ]]; then
        echo "--deposition-id requires a value" >&2
        exit 2
      fi
      deposition_id="$2"
      shift 2
      ;;
    --output-json)
      if [[ $# -lt 2 ]]; then
        echo "--output-json requires a value" >&2
        exit 2
      fi
      output_json="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

python3 tools/audit_publication_readiness.py --require-public
python3 tools/audit_github_release.py --verify-download
python3 tools/audit_publication_log_v112.py

case "$action" in
  dry-run)
    python3 tools/audit_zenodo_upload_readiness.py
    python3 tools/zenodo_upload_v112.py --dry-run --output-json "$output_json"
    ;;
  draft)
    python3 tools/audit_zenodo_upload_readiness.py --require-token
    python3 tools/zenodo_upload_v112.py --output-json "$output_json"
    python3 tools/update_publication_log_v112.py --zenodo-json "$output_json" --apply
    ;;
  sandbox-draft)
    python3 tools/audit_zenodo_upload_readiness.py --require-token --sandbox-token
    python3 tools/zenodo_upload_v112.py --sandbox --output-json "$output_json"
    python3 tools/update_publication_log_v112.py --sandbox --zenodo-json "$output_json" --apply
    ;;
  publish)
    if [[ -z "$deposition_id" ]]; then
      echo "publish requires --deposition-id ID" >&2
      exit 2
    fi
    python3 tools/audit_zenodo_upload_readiness.py --require-token
    python3 tools/zenodo_upload_v112.py \
      --deposition-id "$deposition_id" \
      --publish \
      --output-json "$output_json"
    python3 tools/update_publication_log_v112.py --zenodo-json "$output_json" --apply
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "Unknown action: $action" >&2
    usage >&2
    exit 2
    ;;
esac

echo "Zenodo v1.12 ${action} result JSON: ${output_json}"
