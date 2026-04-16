# Paper Outline (v0.3 — updated 2026-04-16)

## Title
**When Do Foundation Models Pay Off for Retail Demand Forecasting? A Systematic Review and Cross-Benchmark Meta-Analysis**

## Abstract
We present a PRISMA-compliant systematic review of forecasting
methods for short-term retail demand, combined with original
gap-filling experiments that address structural holes in the
literature. We screen ~150 papers (2020–2026) and extract
quantitative results into 185 rows spanning M5, Favorita, and
Rohlik v2. Because no existing paper reports both foundation
models and gradient-boosted trees on these retail datasets under
matched evaluation conditions, we run our own experiments
(Source B: 45 rows from a consumer MacBook + Azure ML batch
sweep) to enable cross-family comparison. A cross-paper pooled
random-effects model (metafor::rma.mv, REML, Knapp-Hartung) on
k = 10 bucket-level deltas finds Δ̂(FM − ML_TREE) = −0.044 WAPE
(95 % CI [−0.11, 0.03], p = 0.17) after excluding the M5
dataset, whose per-series WAPE metric produces a large but
artefactual FM advantage driven by zero-denominator explosions
in the LightGBM baseline. The M5 WAPE cells (Δ ≈ −0.54 to
−0.78) and M5 WRMSSE cell (Δ = +0.41, FM worse) are reported
as a dataset-specific finding, not a family-level effect. We
provide a practitioner-oriented cost-accuracy Pareto analysis
and document that the LightGBM direct-vs-recursive protocol gap
is conditional on demand intermittency (§5.3.6), a finding
vindicated by the gap-filling experiments.

## 1. Introduction (~2 pages, drafted)
- The foundation model wave in time-series forecasting (2024–2026)
- The hype-reality gap: Chronos-2, TimesFM 2.5, Moirai 2.0,
  TiRex — cost and accuracy under realistic retail conditions
- Why a meta-analysis, not another benchmark: too many benchmarks
  (M5, GIFT-Eval, fev-bench), no cross-benchmark synthesis
- Research questions RQ1–RQ4 (see contribution.md)
- **Headline finding preview:** on smooth-demand retail datasets
  (Favorita, Rohlik) the FM-vs-ML_TREE gap is indistinguishable
  from zero; on M5 the apparent gap is a metric artefact
- Contributions (five bullets from contribution.md)

## 2. Background (~3 pages, drafted)
### 2.1 Taxonomy of Forecasting Approaches
- Statistical (Naive, Seasonal Naive, ETS, ARIMA, Croston)
- Machine Learning — global tree models (LightGBM, XGBoost)
- Deep Learning (N-BEATS, DeepAR, TFT, PatchTST)
- Foundation Models (Chronos-2, TiRex, TimesFM 2.5, Moirai 2.0,
  TabPFN-TS) — zero-shot vs fine-tuned, univariate vs covariate

### 2.2 Existing Benchmarks
- M5 Competition (2020) — established but aging; per-series WAPE
  pathology on intermittent demand documented in §5.4.5
- GIFT-Eval (NeurIPS 2024) — 28 datasets, 144K series
- fev-bench (2025) — 100 tasks, 46 with covariates

### 2.3 Systematic Reviews in Forecasting
- Prior meta-analyses (M-competition lineage)
- Gap: no PRISMA-compliant review of foundation models for retail

## 3. Methodology (~4 pages, drafted)
### 3.1 Search Protocol (PRISMA)
- Databases: Scopus, Google Scholar, Semantic Scholar, arXiv
- Search strings and date range (2020–2026)
- Inclusion/exclusion: retail domain, >1000 series, quantitative
  metrics on at least one of {M5, Favorita, Rohlik, GIFT-Eval
  retail tasks, fev-bench retail tasks, Walmart}

### 3.2 Data Extraction (Source A)
- 185-row `analysis/extraction_schema.csv`
- Variables: model, dataset, metric, horizon, n_series,
  has_covariates, zero_shot, hardware, cost
- Row-level paper_id scheme (unique per extracted row)

### 3.3 Gap-Filling Experiments (Source B)
- 45-row `benchmark/results/local_fm_sweep.csv`
- Consumer MacBook MPS: Chronos-Bolt-Tiny (9/9), TiRex (9/9,
  2 cells via CPU fallback)
- Azure ML batch: lightgbm_cov, lightgbm_direct,
  seasonal_naive (27 cells across 3 datasets × 3 horizons)
- Shared paper_id `LOCAL_MAC_<dataset>_h<horizon>` for
  within-paper pairing
- Cost tracking: runtime_sec, cost_usd, co2_kg

### 3.4 Meta-Regression Specification
- Cross-paper pooled Δ: mean(FM) − mean(ML_TREE) per
  (dataset, horizon, metric) bucket
- `rma.mv(yi = delta, V = vi, random = ~1|dataset_norm,
  test = "t", method = "REML")`
- Sampling variance: `vi = (1/n_FM + 1/n_ML_TREE) / n_series_hm`
  for cross-paper pool; `vi = 1/n_valid` for within-paper
- Moderators: dataset_norm, horizon_bucket, has_covariates
  (H1–H3). H4 (interaction) flagged as untestable at k = 10.
- Sensitivity: excl-M5, within-paper-only (Source B)

## 4. Literature Results (~3 pages, drafted)
- PRISMA flow diagram
- Descriptive statistics of the 185 extraction rows
- Narrative synthesis by model family: FM literature evaluates
  on benchmark suites (GIFT-Eval, fev-bench), not on individual
  retail datasets with per-series WAPE — only 2 Source A FM rows
  cover M5/Favorita/Rohlik directly
- Source A has no papers reporting FM *and* ML_TREE under a
  shared paper_id in the retail slice — structural limitation
  driving the cross-paper redesign of §6.1

## 5. Gap-Filling Experiments (~6 pages, already drafted)
### 5.1 Experimental Setup (drafted)
### 5.2 Results — per-dataset LightGBM baselines (drafted)
### 5.3 Baseline Reliability — direct vs recursive (drafted)
  - §5.3.6 conditional synthesis vindicated by Source B
### 5.4 Foundation Models (drafted)
  - §5.4.5 consumer-box results: Table 5.9 (45 cells)
  - §5.4.5 M5 caveat: per-series WAPE + aggregate ratio 0.89
  - §5.4.5 Favorita close call (0.3 pp LGBM win at h=7)
  - §5.4.7 Table 5.9 populated (all 18 FM + baselines)
  - §5.4.9 status: 18/18 FM, 2 TiRex CPU fallback

## 6. Meta-Analysis (~5 pages, already drafted)
### 6.1 Pooling strategy — cross-paper pooled Δ (drafted)
### 6.2–6.6 Moderators, forest plots, Pareto, heterogeneity (drafted)
### 6.7 Preliminary findings (drafted)
  - Cross-paper full: Δ = +0.101, p = 0.505 (n.s.)
  - Cross-paper excl-M5: Δ = −0.044, p = 0.17 (n.s.)
  - Within-paper (Source B only): Δ = −0.245, p = 0.04
  - M5 WAPE vs WRMSSE sign reversal documented
### 6.8 Hypothesis gates (drafted)
  - H1 direction-consistent, H2 needs test, H3 conditional
    (vindicates §5.3.6), H4 untestable at k = 10

## 7. Decision Framework (~2 pages, drafted)
- Flowchart: data characteristics → recommended model family
- Key decision: "if your demand data has <15% zero-day fraction
  and you have covariates, a well-tuned LightGBM matches or
  beats zero-shot FMs on WAPE — save the inference cost"
- When FMs do pay off: univariate cold-start, no historical
  data engineering budget, acceptable ±1 pp WAPE vs LGBM

## 8. Discussion (~2 pages, drafted)
- Data leakage: the elephant in foundation model benchmarking
- Covariate gap: univariate FMs vs covariate-aware ML
- Per-series vs aggregate WAPE: metric choice as a moderator
- Limitations: k = 10 pool, three datasets, no probabilistic
  metrics, Source B on consumer HW only
- Generalizability beyond retail

## 9. Conclusions (~1 page, drafted)
- RQ1: FM advantage is null on smooth-demand retail (Δ = −0.044
  n.s.); M5 effect is metric-specific, not family-level
- RQ2: Intermittency is the load-bearing moderator; covariates
  and protocol direction are conditional on it
- RQ3: Consumer-HW Pareto: FMs 16× cheaper than Azure batch
  in $ but 44× higher CO₂ and 4× slower wall time
- RQ4: Choose LGBM+covariates unless you lack feature
  engineering capacity or face cold-start series

## Appendices
- A: PRISMA checklist
- B: Full search strings
- C: Per-series metric distributions (M5 tail analysis)
- D: Sensitivity analyses (within-paper, excl-M5, WRMSSE)
- E: Full extraction table (extraction_schema.csv snapshot)
- F: Threats to validity — §5.4 foundation model protocol (5 items)
