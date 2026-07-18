# Artifact Map

This file maps manuscript claims to repository artifacts.

## Manuscript

- PDF: `paper/latex/main.pdf`
- LaTeX source: `paper/latex/main.tex` and `paper/latex/section*.tex`
- Bibliography: `paper/references.bib`
- Zenodo v1.0 record: `https://doi.org/10.5281/zenodo.21338004`

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
- Forest plots and descriptive cost-error scatter figures:
  `analysis/figures/figure_*.pdf`

## fev-bench Prediction-Level WAPE Repair

- Official fev-bench runner:
  `benchmark/code/experiments/run_fev_bench_official.py`
- Canonical run manifest:
  `analysis/figures/fev_official_run_manifest.csv`
- Model coverage summary:
  `analysis/figures/fev_official_model_coverage.csv`
- Bootstrap artifact manifest:
  `analysis/figures/fev_official_bootstrap_manifest.csv`
- Summary table used in the manuscript:
  `analysis/figures/fev_prediction_level_wape_summary.csv`
- Chronos-Bolt-Tiny paired WAPE outputs:
  `analysis/figures/fev_chronos_bolt_paired_wape_*.csv`
- Chronos-2 paired WAPE outputs:
  `analysis/figures/fev_chronos2_paired_wape_*.csv`
- TiRex paired WAPE outputs:
  `analysis/figures/fev_tirex_paired_wape_*.csv`
- TimesFM 2.5 paired WAPE outputs:
  `analysis/figures/fev_timesfm25_paired_wape_*.csv`

The full local prediction parquet tree under
`benchmark/results/fev_bench_official/` is intentionally not versioned in git.
Recreate it with the commands documented in `REPRODUCING.md`.

## Source B Experiments

- Exported Source B sweep: `benchmark/results/local_fm_sweep.csv`
- Matched-panel Source B contrasts:
  `analysis/figures/source_b_paired_panel_fm_vs_best_baseline.csv`
- Matched-panel Source B covariance:
  `analysis/figures/source_b_paired_panel_logratio_covariance.csv`
- Matched-panel Source B run ledger:
  `analysis/figures/source_b_paired_panel_run_ledger.csv`
- Legacy Source B cost totals:
  `analysis/figures/source_b_cost_total.csv`
- Legacy Source B cost by dataset/family:
  `analysis/figures/source_b_cost_by_dataset_family.csv`
- Baseline cost consistency audit:
  `analysis/figures/source_b_cost_consistency_audit.csv` and
  `analysis/figures/source_b_cost_consistency_audit.tex`
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
- Full fev-bench prediction parquet outputs under
  `benchmark/results/fev_bench_official/`.
- Downloaded model checkpoints such as TabPFN weights.
- Python/R virtual environments and caches.
