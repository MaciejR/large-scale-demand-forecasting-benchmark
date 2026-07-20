#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PDF_PATH="paper/latex/main.pdf"
TEXT_PATH="${TMPDIR:-/tmp}/v112_manuscript_text.txt"

if [[ ! -f "$PDF_PATH" ]]; then
  echo "Missing manuscript PDF: $PDF_PATH" >&2
  exit 1
fi

if ! command -v pdftotext >/dev/null 2>&1; then
  echo "pdftotext is required for manuscript text audit" >&2
  exit 1
fi

pdftotext "$PDF_PATH" "$TEXT_PATH"

forbidden_pdf_patterns=(
  "Appendix Appendix"
  "Removed Funnel Plot"
  "Pareto frontier"
  "k = 138"
  "k=138"
  "30+ queries"
)

for pattern in "${forbidden_pdf_patterns[@]}"; do
  if grep -Fq "$pattern" "$TEXT_PATH"; then
    echo "Forbidden PDF text found: $pattern" >&2
    exit 1
  fi
done

forbidden_pdf_regexes=(
  'v1\.1([^0-9]|$)'
  'v1\.2([^0-9]|$)'
)

for pattern in "${forbidden_pdf_regexes[@]}"; do
  if grep -Eq "$pattern" "$TEXT_PATH"; then
    echo "Forbidden PDF text found by regex: $pattern" >&2
    exit 1
  fi
done

required_pdf_patterns=(
  "Omitted Asymmetry Diagnostics"
  "Cost-Error Scatter"
  "Total auditable query families: 25"
  "Source A external studies included:"
  "not a validated sampling variance"
  "confirmatory pooled meta-analysis"
)

for pattern in "${required_pdf_patterns[@]}"; do
  if ! grep -Fq "$pattern" "$TEXT_PATH"; then
    echo "Required PDF text missing: $pattern" >&2
    exit 1
  fi
done

forbidden_source_patterns=(
  "Appendix Appendix"
  "Removed Funnel Plot"
  "30+ queries"
  "k = 138"
  "k=138"
)

for pattern in "${forbidden_source_patterns[@]}"; do
  if rg -Fq "$pattern" paper/latex; then
    echo "Forbidden LaTeX source text found: $pattern" >&2
    exit 1
  fi
done

echo "Manuscript audit passed for $PDF_PATH"
