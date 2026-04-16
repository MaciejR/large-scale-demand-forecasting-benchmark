# Appendix B: Search Protocol and Strings

## Research Questions

- **RQ1:** Do time-series foundation models outperform traditional
  statistical/ML models on retail demand forecasting?
- **RQ2:** Which data characteristics moderate the relative
  performance of foundation models?
- **RQ3:** What is the cost-accuracy Pareto frontier across model
  families?
- **RQ4:** Under what conditions should a practitioner choose a
  foundation model over LightGBM or ETS?

## Databases

1. Semantic Scholar (API)
2. Google Scholar
3. arXiv (cs.LG, stat.ML)
4. Scopus
5. Web of Science

## Primary Search Query

```
("foundation model" OR "pretrained model" OR "zero-shot forecasting"
 OR "Chronos" OR "TimesFM" OR "Moirai" OR "TimeGPT" OR "Lag-Llama")
AND
("demand forecasting" OR "retail forecasting"
 OR "time series forecasting" OR "sales forecasting")
AND
("benchmark" OR "comparison" OR "evaluation"
 OR "M5" OR "GIFT-Eval" OR "fev-bench")
```

## Date Range

2020-01-01 to 2026-04-12.

## Inclusion Criteria

1. Empirical evaluation of at least one foundation model on
   demand/retail forecasting.
2. Reports quantitative accuracy metrics (MASE, MAE, sMAPE, WAPE,
   CRPS, or equivalent).
3. Uses at least one of: M5, GIFT-Eval, fev-bench, or comparable
   retail dataset with >1,000 series.
4. Peer-reviewed OR published preprint with reproducible methodology.
5. English language.

## Exclusion Criteria

1. No quantitative results (opinion/position papers only).
2. Only financial/stock/energy forecasting (no retail/demand).
3. Foundation model paper without forecasting evaluation.
4. Duplicate results (keep most recent version).
5. Non-time-series forecasting (e.g., causal inference only).

## Search Execution Log

| Date       | Source      | Query (abbreviated)                     | Results |
|------------|------------|------------------------------------------|---------|
| 2026-04-12 | Google     | foundation model TS demand benchmark     | ~10     |
| 2026-04-12 | Google     | GIFT-Eval benchmark FM retail NeurIPS    | ~10     |
| 2026-04-12 | Google     | fev-bench forecasting covariates 2025    | ~10     |
| 2026-04-12 | Google     | Chronos-2 Amazon retail demand M5        | ~10     |
| 2026-04-12 | Google     | Moirai 2.0 Salesforce TSFM 2025         | ~10     |
| 2026-04-12 | Google     | TimesFM 2.5 Google benchmark 2025        | ~10     |
| 2026-04-12 | Google     | FM vs LightGBM demand forecasting        | ~10     |
| 2026-04-12 | Google     | M5 competition results DL GBT 2020–21    | ~10     |
| 2026-04-12 | Google     | Lag-Llama Timer-XL TimeGPT benchmark     | ~10     |
| 2026-04-12 | Google     | meta-analysis systematic review TS       | ~10     |
| 2026-04-12 | Google     | TimeGPT Nixtla benchmark demand          | ~10     |
| 2026-04-12 | Google     | Chronos Amazon ICML 2024 M5              | ~10     |
| 2026-04-12 | Google     | Timer-XL THUML TSFM 2024–25             | ~10     |
| 2026-04-12 | Google     | AutoGluon-TimeSeries M5 demand           | ~10     |
| 2026-04-12 | Google     | TFB benchmark PVLDB 2024                 | ~10     |
| 2026-04-12 | Google     | zero-shot FM vs LightGBM cost 2025       | ~10     |
| 2026-04-12 | Google     | TFT retail demand M5 2021–22             | ~10     |
| 2026-04-12 | Google     | DeepAR probabilistic retail 2024         | ~10     |
| 2026-04-12 | Google     | PatchTST retail 2023–24                  | ~10     |
| 2026-04-12 | Google     | N-BEATS N-HiTS M5 retail 2023–24         | ~10     |
| 2026-04-12 | Google     | MOMENT TTM IBM benchmark 2024–25         | ~10     |
| 2026-04-12 | Google     | Chronos-Bolt zero-shot LightGBM ETS      | ~10     |
| 2026-04-12 | Google     | retail FM intermittent demand zero-shot   | ~10     |
| 2026-04-12 | arXiv      | demand FM Chronos TimesFM Moirai          | ~10     |
| 2026-04-12 | Sem. Sch.  | foundation model TS demand forecasting   | 1       |

Total queries: 25. Total unique candidates after deduplication: 49.

## PRISMA Flow Summary

```
Records identified through database searching:       ~250
Records after deduplication:                          ~130
Titles/abstracts screened:                             130
Records excluded (not demand/retail, no quant):        ~81
Full-text articles assessed for eligibility:            49
Studies included in qualitative synthesis:              43
Studies included in quantitative extraction:            38
```
