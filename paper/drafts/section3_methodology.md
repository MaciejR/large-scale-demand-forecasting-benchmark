# §3 Methodology (v0.1 draft — 2026-04-16)

This section describes the three-phase protocol: search and
extraction (Source A), gap-filling experiments (Source B), and the
meta-regression specification that combines them.

### 3.1 Search protocol (PRISMA)

We follow the PRISMA 2020 reporting guidelines (Page et al., 2021)
for systematic reviews. The full search protocol is committed at
`analysis/prisma_search_protocol.md`; we summarise the key
parameters here.

**Databases.** Scopus, Google Scholar, Semantic Scholar API, arXiv
(cs.LG, stat.ML), and Web of Science.

**Search query.** We combine three concept blocks with AND:

1. *Foundation model identifiers:* "foundation model", "pretrained
   model", "zero-shot forecasting", Chronos, TimesFM, Moirai,
   TimeGPT, Lag-Llama, TiRex, TabPFN.
2. *Demand forecasting:* "demand forecasting", "retail forecasting",
   "time series forecasting", "sales forecasting".
3. *Benchmark anchors:* "benchmark", "comparison", "evaluation", M5,
   GIFT-Eval, fev-bench.

**Date range.** 2020-01-01 to 2026-04-12. The lower bound captures
the M5 competition and pre-FM baselines; the upper bound is the
extraction lock date.

**Inclusion criteria.** (1) Empirical evaluation of at least one
foundation model on demand or retail forecasting. (2) Reports
quantitative accuracy metrics (WAPE, MASE, MAE, sMAPE, CRPS, WRMSSE,
or win-rate/skill-score equivalents). (3) Uses at least one of M5,
Favorita, Rohlik v2, GIFT-Eval (retail tasks), fev-bench (retail
tasks), or Walmart. (4) Peer-reviewed or published preprint with
reproducible methodology. (5) English language.

**Exclusion criteria.** (1) No quantitative results (position papers,
surveys without new data). (2) Only financial, stock, or energy
forecasting with no retail overlap. (3) FM paper without forecasting
evaluation (architecture-only). (4) Duplicate results — keep most
recent version. (5) Non-time-series forecasting (causal inference
only).

### 3.2 Data extraction (Source A)

Each included study is extracted into one or more rows of the
structured CSV `analysis/extraction_schema.csv` (185 rows as of
2026-04-15). The schema has 23 fields per row:

| Field | Type | Description |
|-------|------|-------------|
| `paper_id` | char | Unique row-level ID (e.g., `A01_chronos_indomain`) |
| `authors` | char | First author et al. |
| `year` | int | Publication year |
| `title` | char | Paper title |
| `venue` | char | Journal, conference, or "this study" |
| `dataset` | char | Raw dataset name as reported |
| `dataset_variant` | char | Sub-dataset or task identifier |
| `n_series` | char | Number of series (free text) |
| `series_length_median` | char | Median series length |
| `frequency` | char | Data frequency (D, W, M, mixed) |
| `has_covariates` | char | Yes / No / mixed |
| `model_name` | char | Model name as reported |
| `model_family` | char | Normalised family tag (§2.1) |
| `zero_shot` | char | Yes / No / mixed |
| `fine_tuned` | char | Yes / No |
| `horizon` | char | Forecast horizon (free text) |
| `eval_method` | char | rolling / rolling-tail / fixed_origin |
| `metric_name` | char | Metric name |
| `metric_value` | char | Reported value (free text, incl. "best") |
| `runtime_reported` | char | Whether runtime is reported |
| `gpu_hours` | char | GPU hours if reported |
| `hardware` | char | Hardware description |
| `notes` | char | Free-text provenance notes |

**Row-level IDs.** Each extracted result is a separate row with a
unique `paper_id`. A paper reporting Chronos and LightGBM on M5
contributes at least two rows (`A01_chronos_indomain`,
`A01_chronos_zeroshot`, etc.). This scheme means that
`group_by(paper_id)` in the meta-regression returns singleton groups
for most rows — a structural property that motivated the cross-paper
pooling design of §6.1.

**Category prefixes.** `A` = FM papers (17 papers, 58 rows), `B` =
benchmark papers (4 papers, 40 rows), `C` = retail ML/DL papers (8
papers, 31 rows), `D` = cross-domain papers (3 papers, 3 rows), `F`
= fev-bench entries (1 paper, 8 rows), `OWN_*` = our own baseline
runs from §5.2–5.3 (6 experiment blocks, 45 rows).

**Normalisation.** Raw `dataset` values are collapsed to five
canonical names (M5, Favorita, Rohlik, fev-bench, Walmart) by the
R function `normalize_dataset()` in `analysis/meta_regression.R`.
Raw `model_family` values are collapsed to four analysis families
(FM, ML_TREE, STATS, NN) by `normalize_family()`. Rows that do not
map to a canonical dataset or family are excluded from the primary
meta-regression but retained in the schema for provenance.

### 3.3 Gap-filling experiments (Source B)

Source A has two structural gaps: (1) no FM paper reports per-series
WAPE on M5, Favorita, or Rohlik under a rolling-origin protocol
matching §5.1.3 — the FM literature evaluates on benchmark suites
(GIFT-Eval, fev-bench), not on individual retail datasets. (2) No
paper reports both FM and ML_TREE on the same retail dataset under
matched conditions with a shared paper_id, so within-paper pairing
(the original §6.1 Pass 1 design) is structurally empty on
Source A.

Source B fills these gaps with 45 rows from two hardware backends:

**Consumer MacBook (M_SERIES_MAC).** Apple M3 Air, 16 GB unified
memory, PyTorch MPS backend. Two FM models:
- **Chronos-Bolt-Tiny** (9 M params, encoder-only): 9/9 cells
  (3 datasets × 3 horizons), all on MPS.
- **TiRex** (~35 M params, xLSTM): 9/9 cells. Seven completed on
  MPS; two (Rohlik h=14, h=28) required CPU fallback
  (`TIREX_FORCE_CPU=1`) due to a pathological MPS dispatch in
  `xlstm_kernels` that stalled at <3 min CPU per hour wall time.

**Azure ML batch (AZURE_E4DS_V4).** Standard_E4ds_v4 (4 vCPU, 32 GB),
CPU-only. Three baseline models:
- **lightgbm_cov** (LightGBM recursive, Tweedie + 6 covariates):
  9 cells.
- **lightgbm_direct** (LightGBM direct, Tweedie + 6 covariates,
  per-horizon head): 9 cells.
- **seasonal_naive**: 9 cells.

All 45 cells use the §5.1.3 evaluation protocol: rolling-origin
with 100 sampled series per cell, per-series WAPE as the primary
metric, and a fixed random seed for reproducibility. Runtime, cost,
and CO₂ are logged per run via MLflow (local file store for MacBook
runs, Azure ML workspace for batch runs). The export script
`tools/export_mlflow_to_csv.py` pulls both backends into a single
CSV keyed on the shared `paper_id = LOCAL_MAC_<dataset>_h<horizon>`,
which is what enables within-paper Δ computation in the R pipeline.

### 3.4 Meta-regression specification

The primary estimand is the cross-paper pooled delta:

> For each (dataset, horizon, metric) bucket that contains at least
> one FM row and at least one ML_TREE row from any source (A or B),
> compute Δ = mean(FM metric values) − mean(ML_TREE metric values).

This produces k = 10 bucket-level deltas (Favorita × 3 horizons ×
WAPE, M5 × 3 horizons × WAPE, M5 × long × WRMSSE, Rohlik × 3
horizons × WAPE). The model is:

```
rma.mv(yi = delta, V = vi,
       random = ~ 1 | dataset_norm,
       data = delta_cross,
       test = "t",         # Knapp-Hartung
       method = "REML")
```

where `vi` is the per-bucket sampling variance proxy defined above.

**Random effect.** `~ 1 | dataset_norm` clusters on dataset because
each Δ mixes rows from multiple papers and the within-paper
anchoring is lost by construction. The dataset level captures the
primary source of heterogeneity (M5 vs smooth-demand datasets).

**Variance.** For the cross-paper pooled design, the per-bucket
sampling variance is `vi = (1/n_FM + 1/n_ML_TREE) / n_series_hm`,
where `n_FM` and `n_ML_TREE` are the number of FM and ML_TREE rows
entering the bucket and `n_series_hm` is the harmonic mean of the
per-row series counts within the bucket. This proxy weights buckets
with more source rows and larger datasets more precisely than
uniform variance. For within-paper paired Δ (Source B cells),
`vi = 1/n_valid = 0.01` because each cell samples 100 series
(§5.1.3). The proxy does not capture within-series error
correlation or between-paper protocol heterogeneity; these are
flagged as limitations in §8.4.

**Small-sample adjustment.** `test = "t"` invokes the Knapp-Hartung
adjustment, replacing the standard normal reference distribution with
a t-distribution whose degrees of freedom equal k − p (where p is
the number of estimated coefficients). This is critical at k = 10.

**Moderator regressions.** We test three moderators individually:

1. `mods = ~ dataset_norm` — tests whether the FM-vs-ML_TREE gap
   varies by dataset (H1 proxy for intermittency, since M5 is the
   only high-intermittency dataset in the pool).
2. `mods = ~ horizon_bucket` — tests whether longer horizons widen
   or narrow the gap.
3. `mods = ~ has_covariates` — tests whether covariate-rich ML_TREE
   baselines reduce FM advantage (H2).

**Sensitivity analyses.** Two pre-registered sensitivity runs:

- **Excl-M5:** Drops all M5 cells and refits on k = 6
  (Favorita + Rohlik WAPE buckets only). This is the cleanest test
  of whether FMs outperform ML_TREE on smooth-demand retail.
- **Within-paper only (Source B):** Reverts to the original strict
  `group_by(paper_id, dataset_norm, horizon_bucket, metric_name)`
  design, which yields k = 9 cells all from `LOCAL_MAC_*`. This
  tests whether the cross-paper pooling design materially changes
  the conclusion.

**Implementation.** All fits are computed by `analysis/
meta_regression.R` using the `metafor` R package (Viechtbauer,
2010). Outputs (forest plots, intercept tables, cell-level CSVs)
are committed to `analysis/figures/`.
