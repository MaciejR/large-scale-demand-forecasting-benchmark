# Large-Scale Retail Demand Forecasting Benchmark

This repository contains the manuscript, extraction table, experiment code, and
analysis outputs for:

**When Do Foundation Models Pay Off for Retail Demand Forecasting?  
A Systematic Review and Cross-Benchmark Meta-Analysis**

The current manuscript PDF is available at
[`paper/latex/main.pdf`](paper/latex/main.pdf).

## What Is In This Repository

- `paper/latex/` - LaTeX manuscript source and compiled PDF.
- `analysis/` - systematic-review extraction table, PRISMA protocol, R
  meta-regression pipeline, and generated figures/tables.
- `benchmark/code/` - experiment runners, model wrappers, data loaders, metrics,
  and cost accounting used for the Source B gap-filling experiments.
- `benchmark/results/` - exported experiment result tables used by the paper.
- `tests/` - lightweight unit tests for loaders, metrics, model wrappers, and
  cost accounting.

Raw Kaggle datasets, local MLflow stores, model checkpoints, and local logs are
not versioned. See [`REPRODUCING.md`](REPRODUCING.md) for setup and rerun
instructions.

## Main Reproducible Artifacts

- Systematic extraction: [`analysis/extraction_schema.csv`](analysis/extraction_schema.csv)
- Source B local/Azure result export:
  [`benchmark/results/local_fm_sweep.csv`](benchmark/results/local_fm_sweep.csv)
- Primary model-level deltas:
  [`analysis/figures/table_6_1_model_level_deltas.csv`](analysis/figures/table_6_1_model_level_deltas.csv)
- Best-baseline sensitivity deltas:
  [`analysis/figures/table_6_1_model_level_deltas_best_baseline.csv`](analysis/figures/table_6_1_model_level_deltas_best_baseline.csv)
- Primary meta-regression output:
  [`analysis/figures/table_6_1_primary_intercept.txt`](analysis/figures/table_6_1_primary_intercept.txt)
- Best-baseline sensitivity:
  [`analysis/figures/sensitivity_best_baseline.txt`](analysis/figures/sensitivity_best_baseline.txt)

## Quick Verification

From the repository root:

```bash
Rscript analysis/meta_regression.R
cd paper/latex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The R script regenerates the analysis outputs under `analysis/figures/`. The
LaTeX commands rebuild the manuscript PDF.

## Data Availability

The repository includes derived extraction and result tables, not the raw
competition datasets. Raw datasets must be downloaded from their original
sources:

- M5 Forecasting Accuracy, Kaggle.
- Corporacion Favorita Grocery Sales Forecasting, Kaggle.
- Rohlik Sales Forecasting Challenge v2, Kaggle / Rohlik challenge release.
- fev-bench and GIFT-Eval results are represented in the extraction scripts and
  extraction table.

## Current Status

The repository is prepared for collaborator review. The manuscript still uses
author/affiliation placeholders in `paper/latex/main.tex`; fill those before
arXiv or journal submission.
