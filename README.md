# Large-Scale Retail Demand Forecasting Benchmark

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21338004.svg)](https://doi.org/10.5281/zenodo.21338004)

This repository contains the manuscript, extraction table, experiment code, and
analysis outputs for:

**When Do Foundation Models Pay Off for Retail Demand Forecasting?  
A Benchmark Study with Structured Literature Search**

The current manuscript PDF is available at
[`paper/latex/main.pdf`](paper/latex/main.pdf).

The v1.0 technical-report release is archived on Zenodo:
<https://doi.org/10.5281/zenodo.21338004>.

The current IJF submission-ready release package is published as GitHub release
[`v1.21`](https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.21)
and can also be rebuilt locally as
`release/v1.21/v1.21-ijf-submission-ready.zip`. It contains the public manuscript,
the double-anonymized review manuscript, submission documents, replication
materials, `COMMIT.txt`, and `CHECKSUMS.txt`; raw Kaggle data, MLflow stores,
model checkpoints, logs, caches, and full fev-bench prediction parquet trees
are intentionally excluded. The submission checklist and tracking record are
in [`docs/IJF_SUBMISSION_CHECKLIST.md`](docs/IJF_SUBMISSION_CHECKLIST.md) and
[`docs/IJF_SUBMISSION_LOG.md`](docs/IJF_SUBMISSION_LOG.md).
The historical v1.12 publication procedure remains available in
[`docs/PUBLICATION_HANDOFF_V1.12.md`](docs/PUBLICATION_HANDOFF_V1.12.md).

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
- The matched-panel Source B analysis runs M5/Rohlik/Favorita on shared
  100-series panels for completed local models and reports paired bootstrap
  contrasts separately from the Source A benchmark analysis. The best local
  baseline pool includes 10-trial tuned recursive and tuned direct LightGBM
  comparators.
- The fev-bench WAPE covariance analysis runs official retail windows for
  Seasonal Naive, Chronos-Bolt-Tiny, Chronos-2, TiRex, and TimesFM 2.5, producing
  prediction-level paired bootstrap covariance matrices for 20 retail tasks.
- Cost-accuracy tradeoffs matter: some foundation-model gains are meaningful
  only when inference cost and hardware constraints are acceptable for the use
  case.

## How to Cite

For the current release package, cite the repository version or the
corresponding Zenodo archive once minted:

```text
Rubczynski, M. (2026). When Do Foundation Models Pay Off for Retail Demand
Forecasting? A Benchmark Study with Structured Literature Search (v1.21).
GitHub. https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.21
```

The historical v1.0 technical-report record remains citable under its original
title:

```text
Rubczyński, M. (2026). When Do Foundation Models Pay Off for Retail Demand
Forecasting? A Systematic Review and Cross-Benchmark Meta-Analysis (v1.0).
Zenodo. https://doi.org/10.5281/zenodo.21338004
```

BibTeX:

```bibtex
@misc{rubczynski2026foundationmodelsretail_v121,
  author       = {Rubczynski, Maciej},
  title        = {When Do Foundation Models Pay Off for Retail Demand Forecasting?
                  A Benchmark Study with Structured Literature Search},
  year         = {2026},
  version      = {v1.21},
  url          = {https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.21}
}

@misc{rubczynski2026foundationmodelsretail_v1,
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

Version v1.21 freezes the current evidence base for journal review. Source B
has matched-panel covariance for all five local FMs on M5/Rohlik/Favorita, and
the fev-bench retail WAPE slice has prediction-level paired covariance for
Chronos-Bolt-Tiny, Chronos-2, TiRex, and TimesFM 2.5 against Seasonal Naive.
Full prediction-level covariance for SQL, MASE, and GIFT-Eval, further baseline
families, and additional FMs are post-submission extensions unless requested by
reviewers.

## What Is In This Repository

- `paper/latex/` - LaTeX manuscript source and compiled PDF.
- `analysis/` - structured-search extraction table, analysis scripts, and
  generated figures/tables.
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
- Study characteristics and risk-of-bias assessment:
  [`analysis/study_characteristics.csv`](analysis/study_characteristics.csv)
  and [`analysis/risk_of_bias_assessment.csv`](analysis/risk_of_bias_assessment.csv)
- Best-baseline sensitivity deltas:
  [`analysis/figures/table_6_1_model_level_deltas_best_baseline.csv`](analysis/figures/table_6_1_model_level_deltas_best_baseline.csv)
- Primary meta-regression output:
  [`analysis/figures/table_6_1_primary_intercept.txt`](analysis/figures/table_6_1_primary_intercept.txt)
- Best-baseline sensitivity:
  [`analysis/figures/sensitivity_best_baseline.txt`](analysis/figures/sensitivity_best_baseline.txt)
- Source B matched-panel contrasts:
  [`analysis/figures/source_b_paired_panel_fm_vs_best_baseline.csv`](analysis/figures/source_b_paired_panel_fm_vs_best_baseline.csv)
- Source B LightGBM tuning trials:
  [`analysis/figures/source_b_paired_panel_lightgbm_tuning_trials.csv`](analysis/figures/source_b_paired_panel_lightgbm_tuning_trials.csv)
- Source B M5 stratified-panel Chronos sensitivity:
  [`analysis/figures/source_b_m5_stratified_chronos_contrasts.csv`](analysis/figures/source_b_m5_stratified_chronos_contrasts.csv)
- Source B matched-panel contrasts currently include Chronos-Bolt-Tiny,
  Chronos-2, Moirai 2.0-Small, batched TiRex, and TimesFM 2.5 on the
  M5/Rohlik/Favorita 100-series panels against the best observed local
  baseline, including tuned recursive and tuned direct LightGBM where they win
  the cell.
- The Source B matched-panel report is generated by
  [`analysis/source_b_paired_panel_report.py`](analysis/source_b_paired_panel_report.py)
  with deterministic sorting and dataset-split bootstrap seeds, so reruns are
  stable across repeated execution and `--runs` ordering.
- Source B cost audit:
  [`analysis/figures/source_b_cost_total.csv`](analysis/figures/source_b_cost_total.csv),
  [`analysis/figures/source_b_cost_by_dataset_family.csv`](analysis/figures/source_b_cost_by_dataset_family.csv), and
  [`analysis/figures/source_b_cost_consistency_audit.csv`](analysis/figures/source_b_cost_consistency_audit.csv)
- fev-bench official run coverage:
  [`analysis/figures/fev_official_model_coverage.csv`](analysis/figures/fev_official_model_coverage.csv)
- fev-bench prediction-level WAPE covariance summary:
  [`analysis/figures/fev_prediction_level_wape_summary.csv`](analysis/figures/fev_prediction_level_wape_summary.csv)
- fev-bench paired WAPE covariance outputs:
  [`analysis/figures/fev_chronos_bolt_paired_wape_covariance.csv`](analysis/figures/fev_chronos_bolt_paired_wape_covariance.csv) and
  [`analysis/figures/fev_chronos2_paired_wape_covariance.csv`](analysis/figures/fev_chronos2_paired_wape_covariance.csv) and
  [`analysis/figures/fev_tirex_paired_wape_covariance.csv`](analysis/figures/fev_tirex_paired_wape_covariance.csv) and
  [`analysis/figures/fev_timesfm25_paired_wape_covariance.csv`](analysis/figures/fev_timesfm25_paired_wape_covariance.csv)

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
  The fev-bench WAPE covariance analysis can be regenerated from the official fev-bench
  datasets via `benchmark/code/experiments/run_fev_bench_official.py`; full
  local prediction parquet outputs are intentionally not tracked in git.

## Current Status

The v1.0 technical report has been published on Zenodo with DOI
`10.5281/zenodo.21338004`. Later release packages are maintained separately and
do not overwrite that historical snapshot. The current working version is
v1.21, which freezes the v1.20 IJF evidence base and adds double-anonymized
submission materials, a 100--150-word abstract, an explicit generative-AI
declaration, and release-hygiene checks. The package records the exact source
commit in `COMMIT.txt` and package integrity in `CHECKSUMS.txt`; the public
GitHub release is
<https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.21>.
