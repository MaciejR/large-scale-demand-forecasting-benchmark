# Large-Scale Retail Demand Forecasting Benchmark

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21338004.svg)](https://doi.org/10.5281/zenodo.21338004)

This repository contains the manuscript, extraction table, experiment code, and
analysis outputs for:

**When Do Foundation Models Pay Off for Retail Demand Forecasting?  
A PRISMA-Informed Cross-Benchmark Reanalysis**

The current manuscript PDF is available at
[`paper/latex/main.pdf`](paper/latex/main.pdf).

The v1.0 technical-report release is archived on Zenodo:
<https://doi.org/10.5281/zenodo.21338004>.

## Key Findings

- Foundation models show negative benchmark-level log-ratio point estimates
  against conventional baselines, but conservative suite/study-level
  uncertainty is wide.
- The advantage is strongest on distributional metrics such as Scaled Quantile
  Loss and smaller on point-forecast metrics such as WAPE.
- Model scale in the 9M--200M parameter range is not a significant moderator in
  the analyzed retail-demand benchmarks.
- Strong conventional baselines remain competitive, especially when covariates,
  leakage controls, and direct-vs-recursive protocol choices are handled
  carefully.
- The matched-panel Source B repair reruns M5/Rohlik/Favorita on shared
  100-series panels for completed local models and reports paired bootstrap
  contrasts separately from the Source A reanalysis.
- Cost-accuracy tradeoffs matter: some foundation-model gains are meaningful
  only when inference cost and hardware constraints are acceptable for the use
  case.

## How to Cite

Please cite the Zenodo technical-report record:

```text
Rubczyński, M. (2026). When Do Foundation Models Pay Off for Retail Demand
Forecasting? A Systematic Review and Cross-Benchmark Meta-Analysis (v1.0).
Zenodo. https://doi.org/10.5281/zenodo.21338004
```

BibTeX:

```bibtex
@misc{rubczynski2026foundationmodelsretail,
  author       = {Rubczynski, Maciej},
  title        = {When Do Foundation Models Pay Off for Retail Demand Forecasting?
                  A Systematic Review and Cross-Benchmark Meta-Analysis},
  year         = {2026},
  publisher    = {Zenodo},
  version      = {v1.0},
  doi          = {10.5281/zenodo.21338004},
  url          = {https://doi.org/10.5281/zenodo.21338004}
}
```

## Publication Roadmap

The current recommended path is to treat v1.4 as the published exploratory
matched-panel repair release, use the v1.5 Favorita/TimesFM reruns to prepare
a tighter follow-up, and keep full TiRex/GPU work as a separate compute task
before deciding between arXiv and a peer-reviewed forecasting or applied-ML
journal.

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
- Primary model-level log-ratios and audit deltas:
  [`analysis/figures/table_6_1_model_level_deltas.csv`](analysis/figures/table_6_1_model_level_deltas.csv)
- Metric-specific summary:
  [`analysis/figures/table_6_1_metric_specific.csv`](analysis/figures/table_6_1_metric_specific.csv)
- Study characteristics:
  [`analysis/study_characteristics.csv`](analysis/study_characteristics.csv)
- Best-baseline sensitivity deltas:
  [`analysis/figures/table_6_1_model_level_deltas_best_baseline.csv`](analysis/figures/table_6_1_model_level_deltas_best_baseline.csv)
- Primary meta-regression output:
  [`analysis/figures/table_6_1_primary_intercept.txt`](analysis/figures/table_6_1_primary_intercept.txt)
- Best-baseline sensitivity:
  [`analysis/figures/sensitivity_best_baseline.txt`](analysis/figures/sensitivity_best_baseline.txt)
- Source B matched-panel contrasts:
  [`analysis/figures/source_b_paired_panel_fm_vs_best_baseline.csv`](analysis/figures/source_b_paired_panel_fm_vs_best_baseline.csv)
- TiRex 20-series Favorita diagnostic:
  [`analysis/figures/source_b_paired_panel_tirex_20_favorita.csv`](analysis/figures/source_b_paired_panel_tirex_20_favorita.csv)

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

The v1.0 technical report has been published on Zenodo with DOI
`10.5281/zenodo.21338004`. Version 1.4 is published as a separate
matched-panel repair package and does not overwrite the historical v1.0
snapshot. Work toward v1.5 has added Favorita matched-panel reruns and a
TiRex throughput diagnostic.
