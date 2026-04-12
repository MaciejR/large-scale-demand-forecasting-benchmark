# Benchmark Code – Design & Roadmap

This directory contains the **reproducible benchmark implementation** for large-scale, short-term demand forecasting.

The goal is to enable **fair, extensible, and transparent** comparison of forecasting models across thousands of SKUs, tracked via **Azure ML + MLflow**.

---

## 1. Design Principles

- **Single source of truth** for data splits and evaluation
- **Rolling-origin evaluation** only (no single holdout)
- **Global models by default** (scalable to thousands of SKUs)
- **MLflow tracking** for all experiments (params, metrics, artifacts)
- **Azure ML pipelines** for reproducible, scalable execution
- Clear separation between:
  - data loading
  - feature engineering
  - models
  - evaluation

---

## 2. Architecture

```
benchmark/code/
│
├─�� data/
│   └── loaders/
│       ├── m5.py               # M5 Walmart dataset
│       ├── gift_eval.py        # GIFT-Eval sales subset (HuggingFace)
│       └── fev_bench.py        # fev-bench tasks (HuggingFace)
│
├── models/
│   ├── baselines/
│   │   ├── naive.py
│   │   ├── seasonal_naive.py
│   │   └── ets.py
│   ├── ml/
│   │   └── lightgbm.py        # Global LightGBM with lag/rolling features
│   ├── dl/
│   │   ├── nbeats.py
│   │   ├── deepar.py
│   │   ├── tft.py
│   │   └── patchtst.py
│   └── foundation/
│       ├── chronos2.py         # Amazon Chronos-2
│       ├── timesfm.py          # Google TimesFM 2.5
│       └── moirai.py           # Salesforce Moirai 2.0
│
├── evaluation/
│   ├── rolling.py
│   ├── metrics.py
│   └── cost.py                 # Runtime, GPU hours, CO₂ estimates
│
├── experiments/
│   ├── run_m5_baselines.py     # Original standalone runner
│   └── run_model.py            # Azure ML entry point with MLflow
│
├── pipelines/
│   ├── single_model_job.yaml   # Single model Azure ML job
│   └── m5_benchmark.yaml       # Full Phase 1 pipeline
│
├── config/
│   └── m5.yaml                 # Experiment parameters
│
└── environment.yaml            # Conda environment for Azure ML
```

---

## 3. Phase 1 – Statistical & ML Baselines (Current)

### Models
- Naive (last-value repeat)
- Seasonal Naive (same-day-last-week) — TODO
- ETS (Holt-Winters, statsmodels)
- LightGBM (global model with lag/rolling features)

### Datasets
- M5 Forecasting (Walmart, 30K+ series)

### Setup
- Frequency: daily
- Horizons: 7, 14, 28
- Evaluation: rolling-origin
- Tracking: Azure ML + MLflow (nested runs)
- Compute: Azure ML Cluster (STANDARD_E4DS_V4)

---

## 4. Phase 2 – Deep Learning Models

### Models
- N-BEATS / N-BEATSx (interpretable deep learning)
- DeepAR (probabilistic autoregressive)
- Temporal Fusion Transformer (attention + covariates)
- PatchTST (patched transformer)

### Datasets — add
- GIFT-Eval sales subset (HuggingFace: Salesforce/GIFT-Eval)

### New capabilities
- GPU compute on Azure ML
- Probabilistic metrics (CRPS, Pinball loss)

---

## 5. Phase 3 – Foundation Models

### Models
- Chronos-2 (Amazon) — zero-shot + fine-tuned
- TimesFM 2.5 (Google) — zero-shot + fine-tuned
- Moirai 2.0 (Salesforce) — zero-shot + fine-tuned, multivariate native

### Datasets — add
- fev-bench (HuggingFace: autogluon/fev_datasets)
  - 46 tasks with covariates
  - Bootstrapped confidence intervals

### New capabilities
- Zero-shot vs fine-tuned comparison
- Cost–accuracy Pareto frontiers
- Data leakage audit (GIFT-Eval non-leaking protocol)
- CO₂ / GPU-hour tracking

---

## 6. Phase 4 (exploratory) – Graph-Based Models

### Datasets
- SupplyGraph (product graph structure)

### Models
- GNN-based forecasting (TBD based on Phase 3 findings)

---

## 7. Reproducibility Checklist

- [x] Fixed random seeds
- [x] Config-driven experiments (YAML)
- [x] Logged metrics and runtimes (MLflow)
- [ ] Hardware disclosure (auto-logged by Azure ML)
- [ ] Bootstrapped confidence intervals (fev-bench)
- [ ] Data leakage audit

---

## 8. Output Artifacts

- Per-series and aggregated metrics CSV (MLflow artifacts)
- Rank tables (per dataset, per horizon)
- Accuracy vs cost Pareto plots
- Summary table per parent run (MLflow)

---

This roadmap is aligned with **IJF / EJOR / NeurIPS Datasets & Benchmarks** reproducibility expectations.
