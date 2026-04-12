# PRISMA Literature Search Protocol

## Search Strategy

### Research Questions
- **RQ1:** Do time-series foundation models outperform traditional statistical/ML models on retail demand forecasting?
- **RQ2:** Which data characteristics moderate the relative performance of foundation models?
- **RQ3:** What is the cost-accuracy Pareto frontier across model families?
- **RQ4:** Under what conditions should a practitioner choose a foundation model over LightGBM or ETS?

### Databases
1. Semantic Scholar (API)
2. Google Scholar
3. arXiv (cs.LG, stat.ML)
4. Scopus
5. Web of Science

### Search Query
```
("foundation model" OR "pretrained model" OR "zero-shot forecasting" OR "Chronos" OR "TimesFM" OR "Moirai" OR "TimeGPT" OR "Lag-Llama")
AND
("demand forecasting" OR "retail forecasting" OR "time series forecasting" OR "sales forecasting")
AND
("benchmark" OR "comparison" OR "evaluation" OR "M5" OR "GIFT-Eval" OR "fev-bench")
```

### Date Range
2020-01-01 to 2026-04-12

### Inclusion Criteria
1. Empirical evaluation of at least one foundation model on demand/retail forecasting
2. Reports quantitative accuracy metrics (MASE, MAE, sMAPE, WAPE, CRPS, or equivalent)
3. Uses at least one of: M5, GIFT-Eval, fev-bench, or comparable retail dataset
4. Peer-reviewed OR published preprint with reproducible methodology
5. English language

### Exclusion Criteria
1. No quantitative results (opinion/position papers only)
2. Only financial/stock/energy forecasting (no retail/demand)
3. Foundation model paper without forecasting evaluation
4. Duplicate results (keep most recent version)
5. Non-time-series forecasting (e.g., causal inference only)

---

## Initial Paper List (Automated Search — 2026-04-12)

### Tier 1: Primary Benchmarks and Foundation Model Papers

| # | Paper | Year | Key Models | Dataset(s) | Venue |
|---|-------|------|-----------|------------|-------|
| 1 | GIFT-Eval: A Benchmark for General Time Series Forecasting Model Evaluation | 2024 | 17 models incl. Chronos, Moirai, TimesFM, TimeGPT | 23 datasets, 144K series | NeurIPS TSALM Workshop |
| 2 | fev-bench: A Realistic Benchmark for Time Series Forecasting | 2025 | Multiple (with covariates) | 100 tasks, 96 datasets | arXiv (Boston College WP) |
| 3 | TSFM-Bench: Comprehensive Benchmark of Foundation Models for Time Series Forecasting | 2024/2025 | Wide range of TSFMs | Multiple domains | KDD 2025 |
| 4 | FoundTS: Comprehensive and Unified Benchmarking of Foundation Models for Time Series Forecasting | 2024 | Multiple TSFMs | Multiple | OpenReview |
| 5 | M5 accuracy competition: Results, findings, and conclusions | 2022 | LightGBM, ensembles, stat methods | M5 (Walmart) | IJF |
| 6 | The M5 competition: Conclusions | 2022 | All top methods | M5 | IJF |
| 7 | Introducing Chronos-2: From univariate to universal forecasting | 2025 | Chronos-2 | GIFT-Eval, fev-bench | Amazon Science |
| 8 | TimesFM 2.5 | 2025 | TimesFM-2.5 (200M) | GIFT-Eval | Google Research |
| 9 | Moirai 2.0: When Less Is More for Time Series Forecasting | 2025 | Moirai 2.0 | GIFT-Eval | arXiv / Salesforce |
| 10 | Lag-Llama: Towards Foundation Models for Probabilistic Time Series Forecasting | 2023 | Lag-Llama | Multiple | NeurIPS 2023 |

### Tier 2: Demand Forecasting Specific

| # | Paper | Year | Key Models | Dataset(s) | Venue |
|---|-------|------|-----------|------------|-------|
| 11 | Critical Evaluation of Time Series Foundation Models in Demand Forecasting | 2024 | TimeGPT, TimesFM vs traditional | Competition datasets | OpenReview |
| 12 | Comparative Analysis of Modern Machine Learning Models for Retail Sales Forecasting | 2025 | LightGBM, XGBoost, DL, foundation | Retail | arXiv |
| 13 | Foundation Models for Demand Forecasting via Dual-Strategy Ensembling | 2025 | Chronos, LightGBM, DeepAR | Retail demand | arXiv |
| 14 | Benchmarking Time Series Foundation Models for Short-Term Household Electricity Load Forecasting | 2024 | Multiple TSFMs | Electricity (transferable methods) | arXiv |
| 15 | Machine learning algorithms in intermittent demand forecasting: a review | 2025 | LightGBM, CatBoost, ML methods | Intermittent demand | IJPR |

### Tier 3: Surveys and Meta-Studies

| # | Paper | Year | Scope | Venue |
|---|-------|------|-------|-------|
| 16 | Foundation Models for Time Series: A Survey | 2025 | Comprehensive TSFM survey | arXiv |
| 17 | AI and classical statistical models for time series forecasting: comprehensive review | 2025 | 150+ studies meta-analysis | Journal of Big Data |
| 18 | A comprehensive survey of deep learning for time series forecasting | 2025 | Architectural diversity | AI Review (Springer) |
| 19 | Time Series Forecasting Methods: From Statistical to LLMs | 2025 | Full methods landscape | ACM CCBD |
| 20 | A systematic review for transformer-based long-term series forecasting | 2024 | Transformers for TS | AI Review (Springer) |

### Tier 4: To Search (Manual Follow-up Needed)

- TimeGPT (Nixtla) original paper and benchmark results
- Timer-XL (THUML) paper
- TFB benchmark paper (PVLDB 2024 Best Paper Nomination)
- Chronos-1 original paper (ICML 2024)
- AutoGluon-TimeSeries results on M5
- Individual M5 top-method papers (top 5 winners)
- Deutsche Bahn Chronos case study (AWS)
- Grid Dynamics TSFM comparison for demand forecasting
- Any IJF special issues on foundation models

---

## Next Steps

1. [ ] Download full-text PDFs for Tier 1-2 papers
2. [ ] Screen titles/abstracts against inclusion criteria
3. [ ] Forward/backward citation search on key papers
4. [ ] Extract data into `analysis/extraction_schema.csv`
5. [ ] Create PRISMA flow diagram
6. [ ] Identify remaining gaps (model x dataset combinations not covered in literature)
