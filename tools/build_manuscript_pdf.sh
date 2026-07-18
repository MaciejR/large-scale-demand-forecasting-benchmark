#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/paper/latex"

pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/v112_pdflatex1.log
bibtex main >/tmp/v112_bibtex.log
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/v112_pdflatex2.log
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/v112_pdflatex3.log

critical_warnings="$(
  grep -E "Warning--|undefined|Undefined|Citation|Reference|Font Warning|pdfTeX warning" \
    main.log main.blg || true
)"
if [[ -n "$critical_warnings" ]]; then
  echo "Critical LaTeX/BibTeX warnings found:" >&2
  echo "$critical_warnings" >&2
  exit 1
fi

echo "Built paper/latex/main.pdf"
