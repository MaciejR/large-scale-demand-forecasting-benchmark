# Paper Outline

## Title
**Short-Term Demand Forecasting at Scale: A Benchmark of Statistical, ML, and Foundation Models (2026)**

## Abstract
This paper presents a large-scale benchmark of demand forecasting methods for short-term horizons in retail and supply chain settings. We compare statistical baselines, machine learning, deep learning, transformer-based, and time-series foundation models under a unified experimental protocol across established and contemporary benchmarks — M5, GIFT-Eval (sales domain), and fev-bench (tasks with covariates). The study emphasizes forecast accuracy, computational cost, stability, and scalability, with particular focus on whether recent foundation models (Chronos-2, TimesFM 2.5, Moirai 2.0) justify their cost over simpler alternatives. All experiments are tracked via MLflow on Azure ML for full reproducibility.

## 1. Introduction
- Importance of demand forecasting in retail and supply chain management
- Characteristics of short-term, large-scale forecasting problems
- The foundation model revolution (2024–2026) and the question of diminishing returns
- Limitations of existing benchmarks: single-dataset, no covariates, data leakage concerns
- Contributions of this work

## 2. Related Work
### 2.1 Statistical Forecasting Methods
### 2.2 Machine Learning Approaches
### 2.3 Deep Learning Models
### 2.4 Transformer-Based Forecasting
### 2.5 Foundation Models for Time Series
- Chronos / Chronos-2 (Amazon, 2024–2025)
- TimesFM 1.0–2.5 (Google, 2024–2025)
- Moirai / Moirai 2.0 / Moirai-MoE (Salesforce, 2024–2025)
### 2.6 Benchmarking Challenges
- Data leakage in pretraining (TimesFM on GIFT-Eval datasets)
- GIFT-Eval non-leaking pretraining protocol
- fev-bench: covariates, statistical rigor, bootstrapped CIs

## 3. Problem Formulation
- Multi-series short-term forecasting setup
- Global vs local models
- Univariate vs multivariate (covariate-aware) forecasting
- Zero-shot vs fine-tuned foundation models

## 4. Datasets

### 4.1 M5 Forecasting (Walmart, 2020)
- 30,490 product-level daily sales across 10 stores
- Hierarchical aggregation (12 levels, 42,840 series)
- Established baseline for retail demand forecasting
- **Role:** backward compatibility, reproducibility anchor

### 4.2 GIFT-Eval — Sales Domain Subset (Salesforce, NeurIPS 2024)
- Part of 28-dataset, 144K-series benchmark spanning 7 domains
- Sales subset: retail and e-commerce demand series
- Short/medium/long prediction horizons per dataset
- Non-leaking pretraining dataset (230B data points)
- 20 published baselines including foundation models
- **Role:** contemporary multi-domain benchmark, direct comparability with SOTA

### 4.3 fev-bench — Demand Tasks with Covariates (AutoGluon/Amazon, 2025)
- 100 forecasting tasks from 96 datasets, 7 domains
- 46 tasks include covariates (prices, promotions, weather, events)
- Bootstrapped confidence intervals for statistical rigor
- Compatible with GluonTS, darts, AutoGluon, Nixtla, sktime
- **Role:** covariate-aware evaluation, statistical significance testing

### 4.4 SupplyGraph (2024) — exploratory
- Supply chain graph structure: products as nodes, relationships as edges
- GNN-ready format
- **Role:** future extension for graph-based models

## 5. Forecasting Models

### 5.1 Baselines
- Naive (last-value repeat)
- Seasonal Naive (same-day-last-week)
- ETS (Holt-Winters, statsmodels)

### 5.2 Machine Learning
- LightGBM (global model with lag/rolling features)

### 5.3 Deep Learning
- N-BEATS / N-BEATSx
- DeepAR
- Temporal Fusion Transformer (TFT)
- PatchTST

### 5.4 Foundation Models (zero-shot and fine-tuned)
- Chronos-2 (Amazon, T5 encoder-decoder, univariate)
- TimesFM 2.5 (Google, continuous quantile prediction, univariate)
- Moirai 2.0 (Salesforce, any-variate, decoder-only, 36M pretrain series)

## 6. Experimental Setup
- Evaluation protocol: rolling-origin
- Horizons: 7, 14, 28 days (M5); short/medium/long (GIFT-Eval); task-specific (fev-bench)
- Metrics: WAPE (primary), sMAPE, MAE, CRPS (probabilistic)
- Computational cost: training time, inference time, GPU hours, CO₂ estimate
- Infrastructure: Azure ML + MLflow tracking, reproducible YAML pipelines
- Data leakage mitigation: GIFT-Eval non-leaking protocol, separate pretraining

## 7. Results
- Accuracy comparison across datasets and horizons
- Foundation models vs traditional: when do they win?
- Cost–accuracy Pareto frontiers
- Covariate impact (fev-bench tasks with vs without covariates)
- Stability analysis (variance across rolling windows)
- Statistical significance (bootstrapped CIs from fev-bench)

## 8. Discussion
- Practical implications for retail practitioners
- When foundation models justify their cost (and when they do not)
- The covariate gap: univariate foundation models vs covariate-aware ML
- Data leakage: the elephant in foundation model benchmarking
- Scalability: wall-clock time at 30K+ series

## 9. Threats to Validity
- Dataset selection bias
- Foundation model pretraining contamination
- Hardware-dependent runtime comparisons
- Hyperparameter tuning budget fairness

## 10. Conclusions and Future Work
- Practical model selection guidelines
- Foundation model fine-tuning strategies
- Graph-based forecasting (SupplyGraph extension)
- Probabilistic forecast evaluation expansion
