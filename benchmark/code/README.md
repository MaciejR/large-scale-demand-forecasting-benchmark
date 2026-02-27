# Benchmark Code – Design & Roadmap

This directory contains the **reproducible benchmark implementation** for large-scale, short-term demand forecasting.

The goal is to enable **fair, extensible, and transparent** comparison of forecasting models across thousands of SKUs.

---

## 1. Design Principles

- **Single source of truth** for data splits and evaluation
- **Rolling-origin evaluation** only (no single holdout)
- **Global models by default** (scalable to thousands of SKUs)
- Clear separation between:
  - data loading
  - feature engineering
  - models
  - evaluation

---

## 2. Planned Architecture

```
benchmark/code/
│
├── data/
│   ├── loaders/
│   │   ├── m5.py
│   │   ├── favorita.py
│   │   └── rossmann.py
│   └── preprocessing.py
│
├── features/
│   ├── lags.py
│   └── rolling.py
│
├── models/
│   ├── baselines/
│   │   ├── naive.py
│   │   ├── seasonal_naive.py
│   │   └── ets.py
│   ├── ml/
│   │   └── lightgbm.py
│   └── dl/            # added later
│
├── evaluation/
│   ├── rolling.py
│   ├── metrics.py
│   └── cost.py
│
├── experiments/
│   └── run_m5_baselines.py
│
└── config/
│   └── m5.yaml
```

---

## 3. Phase 1 – Baseline Benchmark (Current Milestone)

### Models
- Naive
- Seasonal Naive
- ETS (statsmodels)
- LightGBM (global model)

### Datasets
- M5 Forecasting (core)

### Forecasting Setup
- Frequency: daily
- Horizons: 7, 14, 28
- Evaluation: rolling-origin

---

## 4. Phase 2 – Advanced Models

- N-BEATS / N-BEATSx
- DeepAR
- Temporal Fusion Transformer
- PatchTST

---

## 5. Phase 3 – Foundation Models

- Chronos (zero-shot vs fine-tuned)
- Cost vs accuracy analysis

---

## 6. Reproducibility Checklist

- Fixed random seeds
- Config-driven experiments (YAML)
- Logged metrics and runtimes
- Hardware disclosure

---

## 7. Output Artifacts

- CSV with per-SKU and aggregated metrics
- Rank tables (per dataset, per horizon)
- Accuracy vs cost plots

---

This roadmap is aligned with **IJF / EJOR reproducibility expectations**.
