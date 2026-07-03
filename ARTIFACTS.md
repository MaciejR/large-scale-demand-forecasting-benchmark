# Artifact Map

This file maps manuscript claims to repository artifacts.

## Manuscript

- PDF: `paper/latex/main.pdf`
- LaTeX source: `paper/latex/main.tex` and `paper/latex/section*.tex`
- Bibliography: `paper/references.bib`

## Review and Extraction

- Search protocol: `analysis/prisma_search_protocol.md`
- PRISMA flow generator: `analysis/prisma_flow_diagram.py`
- PRISMA flow outputs: `analysis/figures/prisma_flow.pdf`,
  `analysis/figures/prisma_flow.png`
- Extraction table: `analysis/extraction_schema.csv`
- fev-bench extraction script: `analysis/extract_fev_bench_retail.py`
- GIFT-Eval extraction script: `analysis/extract_gift_eval_retail.py`

## Meta-Regression

- Main pipeline: `analysis/meta_regression.R`
- Primary deltas: `analysis/figures/table_6_1_model_level_deltas.csv`
- Best-baseline deltas:
  `analysis/figures/table_6_1_model_level_deltas_best_baseline.csv`
- Primary intercept: `analysis/figures/table_6_1_primary_intercept.txt`
- Heterogeneity table: `analysis/figures/table_6_2_heterogeneity.csv`
- Moderator outputs: `analysis/figures/moderator_*.txt`
- Sensitivity outputs: `analysis/figures/sensitivity_*.txt`
- Forest/funnel/Pareto figures: `analysis/figures/figure_*.pdf`

## Source B Experiments

- Exported Source B sweep: `benchmark/results/local_fm_sweep.csv`
- Horizon-scaled Favorita direct-LightGBM check:
  `benchmark/results/direct_scaled_favorita.csv`
- Experiment runners: `benchmark/code/experiments/`
- Data loaders: `benchmark/code/data/loaders/`
- Model wrappers: `benchmark/code/models/`
- Metrics/cost code: `benchmark/code/evaluation/`

## What Is Not Versioned

- Raw Kaggle/Rohlik datasets under `data/raw/`.
- Local MLflow stores under `mlruns/`.
- Local logs under `logs/`.
- Downloaded model checkpoints such as TabPFN weights.
- Python/R virtual environments and caches.
