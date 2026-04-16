# Appendix E: Extraction Table (Abbreviated)

The full extraction table (`analysis/extraction_schema.csv`, 185
data rows + 1 header) records one row per (paper × model × dataset ×
metric) observation. The complete CSV is available in the
supplementary materials. Table E.1 shows the key columns; columns
omitted for space include `dataset_variant`, `n_series`,
`series_length_median`, `frequency`, `fine_tuned`, `runtime_reported`,
`gpu_hours`, `hardware`, and `notes`.

## Column Definitions

| Column        | Description                                          |
|---------------|------------------------------------------------------|
| paper_id      | Unique row identifier: `{category}{seq}_{detail}`    |
| authors       | First author et al.                                  |
| year          | Publication year                                     |
| dataset       | Target dataset (M5, Favorita, Rohlik, GIFT-Eval, fev-bench, etc.) |
| model_name    | Model as named by the paper                          |
| model_family  | One of: foundation, deep_learning, ml_tree, statistical, ensemble |
| zero_shot     | Yes / No — whether the model was applied without task-specific training |
| horizon       | Forecast horizon (days) or "mixed" if aggregated     |
| eval_method   | rolling / fixed_origin / competition                 |
| metric_name   | Reported metric (WAPE, WRMSSE, MASE, MAE, sMAPE, WQL, CRPS, win_rate_*) |
| metric_value  | Reported value (numeric or qualitative rank)         |
| has_covariates| Whether the model used exogenous covariates          |

## Row Counts by Category

| Category | Description                          | Rows |
|----------|--------------------------------------|------|
| A        | Foundation model papers              | 48   |
| B        | Benchmark papers                     | 42   |
| C        | M5 competition and retail-specific   | 38   |
| D        | Deep learning baselines              | 12   |
| E        | Surveys and meta-studies             | 7    |
| F        | Cost/efficiency analysis             | 8    |
| OWN      | Our LightGBM baselines (Source B)    | 12   |
| LOCAL    | Our FM experiments (Source B)         | 18   |
| **Total**|                                      | **185** |

## Source A vs Source B

- **Source A** (literature extraction): categories A–F (155 rows
  from 38 studies). These rows report accuracy numbers as published
  by the original authors.
- **Source B** (gap-filling experiments): OWN + LOCAL (30 rows).
  These rows are from our own experiments on consumer hardware
  (MacBook M-series MPS) and Azure ML (E4DS_V4), using the shared
  protocol of §5.1.

The extraction table is frozen at the version used for the
meta-regression of §6. Any post-submission additions would require
re-running the pooled models of §6.7.
