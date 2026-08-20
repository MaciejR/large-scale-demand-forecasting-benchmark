#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

tools/build_manuscript_pdf.sh

(
  cd paper/latex
  pdflatex -interaction=nonstopmode -halt-on-error main_anonymized.tex >/tmp/ijf_anon_pdflatex1.log
  bibtex main_anonymized >/tmp/ijf_anon_bibtex.log
  pdflatex -interaction=nonstopmode -halt-on-error main_anonymized.tex >/tmp/ijf_anon_pdflatex2.log
  pdflatex -interaction=nonstopmode -halt-on-error main_anonymized.tex >/tmp/ijf_anon_pdflatex3.log

  critical_warnings="$(
    grep -E "Warning--|undefined|Undefined|Citation|Reference|Font Warning|pdfTeX warning" \
      main_anonymized.log main_anonymized.blg || true
  )"
  if [[ -n "$critical_warnings" ]]; then
    echo "Critical anonymous-manuscript LaTeX/BibTeX warnings found:" >&2
    echo "$critical_warnings" >&2
    exit 1
  fi
)

if [[ "${SKIP_PRIVATE_TITLE_PAGE:-0}" != "1" ]]; then
  if [[ -n "${IJF_POSTAL_ADDRESS:-}" ]]; then
    python3 tools/build_private_title_page.py --output paper/submission/title_page.pdf
  elif [[ "${ALLOW_INCOMPLETE_TITLE_PAGE:-0}" == "1" ]]; then
    echo "Postal address absent; preserving any existing private title-page PDF"
  else
    echo "Set IJF_POSTAL_ADDRESS before building the private title page" >&2
    exit 1
  fi
fi

SOURCE_DATE_EPOCH=1787184000 TZ=UTC \
  pandoc paper/submission/cover_letter.md --pdf-engine=pdflatex \
  -V geometry:margin=1in -V fontsize=11pt -o paper/submission/cover_letter.pdf

python3 tools/audit_ijf_anonymity.py paper/latex/main_anonymized.pdf

echo "Built IJF manuscript and submission files"
