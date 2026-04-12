# Experimental Protocol

## Evaluation Setup
- Rolling-origin evaluation
- Short-term horizons: 7, 14, 28 days (M5); short/medium/long (GIFT-Eval); task-specific (fev-bench)
- Global models trained across all series

## Datasets

| Dataset | Source | Series | Covariates | Role |
|---------|--------|--------|------------|------|
| M5 | Kaggle (Walmart) | 30,490 | No | Backward-compatible retail baseline |
| GIFT-Eval (sales) | HuggingFace (Salesforce) | Varies | No | Contemporary multi-domain benchmark |
| fev-bench | HuggingFace (AutoGluon) | 100 tasks | 46 with covariates | Statistical rigor, covariate impact |
| SupplyGraph | arXiv | Graph-structured | Graph edges | Exploratory (Phase 4) |

## Metrics

### Point Forecasts
- WAPE (primary) — weighted, robust to scale differences
- sMAPE — symmetric, percentage-based
- MAE — absolute, interpretable

### Probabilistic Forecasts (Phase 2+)
- CRPS (Continuous Ranked Probability Score)
- Pinball loss (quantile-specific)

### Statistical Significance (Phase 3)
- Bootstrapped confidence intervals (fev-bench native)
- Diebold-Mariano test for pairwise model comparison

## Computational Cost
- Training time (wall-clock)
- Inference time (per 1000 series)
- GPU hours (Azure ML auto-logged)
- CO₂ estimate (based on hardware TDP × runtime)
- Hardware configuration disclosure

## Data Leakage Protocol
- GIFT-Eval non-leaking pretraining dataset for foundation models
- Disclosure of which foundation models were pretrained on which evaluation datasets
- Separate reporting for potentially contaminated results
