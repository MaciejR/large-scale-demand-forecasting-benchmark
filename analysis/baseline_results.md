# Phase A Baseline Results: Seasonal Naive on M5

**Pipeline:** `bold_fly_grlqvdx1cg` (Azure ML, swedencentral)
**Date:** 2026-04-13
**Compute:** `cc-forecast-batch` (E4DS_V4, 4 vCPU, 32 GB RAM)
**Environment:** `forecast-benchmark-cpu-env:1`
**Code commit:** `eb3e6528` (post MLflow artifact bug fix)

## Dataset

- **M5 (Walmart)** — 30,490 product-store series, 1,941 days, daily frequency
- 59,181,090 total observations
- High intermittency (many zero days) — Walmart unit sales

## Method

Seasonal Naive with weekly seasonality (period=7). Forecasts horizon h ahead by repeating the
value from h−7, h−14, … steps back. Rolling-origin evaluation: each series uses min_train_size=100
days, then rolls forward generating non-overlapping forecast windows of length h.

## Results

| Horizon | MAE_mean | sMAPE_mean | WAPE_mean | Runtime (s) | Cost (USD) | CO₂ (kg) | Series/sec |
|--------:|---------:|-----------:|----------:|------------:|-----------:|---------:|-----------:|
| 7       | 1.0014   | 59.68      | 1.2853    | 1061.2      | $0.1120    | 0.000287 | 28.7       |
| 14      | 1.0169   | 60.17      | 1.2916    | 784.4       | $0.0828    | 0.000212 | 38.9       |
| 28      | 1.0334   | 60.80      | 1.3047    | 608.9       | $0.0643    | 0.000165 | 50.1       |

## Observations

1. **Error grows slowly with horizon** (MAE 1.0014 → 1.0334 across h=7→28, just +3.2%). This is
   characteristic of intermittent demand: the naive baseline's poor calibration dominates over
   horizon effects.
2. **sMAPE near 60% across all horizons** — confirms M5's well-known difficulty for
   non-cross-learning methods. The M5 paper reports the seasonal-naive benchmark at WRMSSE ≈ 0.85
   while the LightGBM winner achieved 0.520 (Table 3, Makridakis 2022).
3. **Runtime decreases with horizon counterintuitively** — fewer rolling windows fit in the
   training tail, so total per-series work drops. Throughput rises from 28.7 to 50.1 series/sec.
4. **Total compute cost**: $0.26 across all 3 horizons. Negligible compared to GPU foundation
   models (Chronos-2 reports 3.6s median per task on A10G, but ×100 tasks ×retail subset means
   ~$30–$50 for a comparable sweep).

## Cost-accuracy reference points (from literature)

| Model              | Hardware  | Approx. throughput  | Source           |
|--------------------|-----------|---------------------|------------------|
| Seasonal Naive     | E4DS_V4   | 28–50 series/sec    | this study       |
| LightGBM (M5 winner)| CPU      | n/a (220 models)    | C01 (Makridakis) |
| Chronos-2          | A10G GPU  | 300 series/sec      | A02 (Ansari)     |
| Chronos-Bolt       | CPU       | 250× faster than v1 | A11 (AWS)        |
| TabPFN-TS          | GPU       | n/a (11M params)    | A14 (Hollmann)   |

## Next steps

1. Run LightGBM with covariates (calendar + prices + SNAP events) on M5 — primary FM-killer baseline
2. Run ETS/AutoARIMA via statsforecast on M5 for a deeper statistical baseline
3. Once GPU quota is granted (NCASv3_T4 in swedencentral): run Chronos-Bolt zero-shot for cost-accuracy comparison
4. Replicate on Favorita and Rohlik datasets to test cross-dataset stability

## Files

- Logs: `/tmp/sn_h7/artifacts/user_logs/std_log.txt` (and h14, h28)
- MLflow runs: experiment `meta-analysis-gap-filling`, run names `seasonal_naive_m5_h{7,14,28}`
- Pipeline: `benchmark/code/pipelines/gap_filling.yaml`
