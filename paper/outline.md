# Paper Outline

## Title
**When Do Foundation Models Pay Off for Retail Demand Forecasting? A Systematic Review and Cross-Benchmark Meta-Analysis**

## Abstract
We present a PRISMA-compliant systematic review and meta-analysis of forecasting methods for short-term retail demand. We screen ~150-200 papers (2020-2026), extract quantitative results from ~40-60 studies spanning M5, GIFT-Eval, and fev-bench, and run gap-filling experiments where model-dataset combinations are missing from the literature. A random-effects meta-regression identifies data characteristics that moderate foundation model performance relative to traditional approaches. We provide a practitioner-oriented decision framework and cost-accuracy Pareto analysis. All gap-filling experiments are tracked via MLflow on Azure ML.

## 1. Introduction (~2 pages)
- The foundation model wave in time-series forecasting (2024-2026)
- The hype-reality gap: do Chronos-2, TimesFM 2.5, Moirai 2.0 justify their cost?
- Why a meta-analysis, not another benchmark: too many benchmarks, no synthesis
- Research questions (RQ1-RQ4)
- Contributions

## 2. Background (~3 pages)
### 2.1 Taxonomy of Forecasting Approaches
- Statistical (Naive, Seasonal Naive, ETS, ARIMA)
- Machine Learning (LightGBM, XGBoost — global models)
- Deep Learning (N-BEATS, DeepAR, TFT, PatchTST)
- Foundation Models (Chronos-2, TimesFM 2.5, Moirai 2.0) — zero-shot vs fine-tuned

### 2.2 Existing Benchmarks
- M5 Competition (2020) — established but aging
- GIFT-Eval (NeurIPS 2024) — 28 datasets, 144K series, non-leaking protocol
- fev-bench (2025) — 100 tasks, 46 with covariates, bootstrapped CIs

### 2.3 Systematic Reviews in Forecasting
- Prior meta-analyses (M-competition lineage)
- Gap: no PRISMA-compliant review of foundation models for retail

## 3. Methodology (~4 pages)
### 3.1 Search Protocol (PRISMA Phase A)
- Databases: Scopus, Google Scholar, Semantic Scholar, arXiv
- Search strings and date range (2020-2026)
- Inclusion/exclusion criteria (retail domain, >1000 series, quantitative metrics)

### 3.2 Data Extraction
- Variables: model, dataset, metric (WAPE, sMAPE, MAE, CRPS), horizon, n_series, series_length, intermittency, covariates, compute cost

### 3.3 Gap-Filling Experiments (Phase B)
- Foundation models on M5 (not in literature with rolling-origin)
- LightGBM+covariates on fev-bench retail tasks
- Seasonal Naive everywhere (universal baseline)
- Cost tracking: GPU hours, $/1000 series, CO2

### 3.4 Meta-Regression Specification (Phase C)
- Random-effects model
- Moderators: n_series, series_length, intermittency_ratio, has_covariates, horizon_ratio
- Publication bias assessment (funnel plot, Egger's test)

## 4. Literature Results (~4 pages)
- PRISMA flow diagram (identification → screening → eligibility → included)
- Descriptive statistics of included studies
- Narrative synthesis by model family
- Extracted accuracy tables

## 5. Gap-Filling Experiments (~3 pages)
### 5.1 Experimental Setup
- Azure ML infrastructure, rolling-origin evaluation
- Metrics: WAPE (primary), sMAPE, MAE, CRPS
- Horizons: 7/14/28 (M5), short/medium/long (GIFT-Eval), task-specific (fev-bench)

### 5.2 Results
- Foundation models zero-shot on M5
- LightGBM+covariates on fev-bench
- Cost metrics across all runs

## 6. Meta-Analysis (~4 pages)
### 6.1 Overall Effect Sizes
- Forest plots: foundation models vs statistical, vs ML, vs DL

### 6.2 Moderator Analysis
- Which data characteristics predict foundation model advantage?
- Interaction effects (covariates × model family)

### 6.3 Cost-Accuracy Pareto Frontier
- GPU hours vs WAPE improvement
- $/1000 series across model families
- CO2 footprint comparison

### 6.4 Publication Bias
- Funnel plots, Egger's test results

## 7. Decision Framework (~2 pages)
- Flowchart: data characteristics → recommended model family
- Cost thresholds: "foundation model pays off when..."
- Practical implementation guidance for retail teams

## 8. Discussion (~2 pages)
- Data leakage: the elephant in foundation model benchmarking
- Covariate gap: univariate foundation models vs covariate-aware ML
- Limitations of this meta-analysis
- Generalizability beyond retail

## 9. Conclusions (~1 page)
- Key findings per RQ
- Practical recommendations
- Future work: probabilistic forecasting, graph-based models, fine-tuning strategies

## Appendices
- A: PRISMA checklist
- B: Full search strings
- C: Per-series metric distributions
- D: Sensitivity analyses
- E: Full extracted data table
