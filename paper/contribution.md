# Contributions and Positioning

## Research Questions

- **RQ1:** Do time-series foundation models (zero-shot or fine-tuned) outperform traditional statistical/ML models on retail demand forecasting tasks?
- **RQ2:** Which data characteristics (n_series, series_length, intermittency, covariates, horizon_ratio) moderate the relative performance of foundation models?
- **RQ3:** What is the cost-accuracy Pareto frontier across model families when GPU hours, inference latency, and CO2 are considered?
- **RQ4:** Under what conditions should a retail practitioner choose a foundation model over LightGBM or ETS?

## Contributions

1. **First PRISMA-compliant systematic review** of foundation models for retail demand forecasting, synthesizing ~40-60 studies (2020-2026) across M5, GIFT-Eval, and fev-bench.
2. **Gap-filling experiments** providing missing model-dataset combinations (foundation models on M5 with rolling-origin, LightGBM+covariates on fev-bench, Seasonal Naive everywhere) under a unified evaluation protocol.
3. **Meta-regression with moderators** identifying which data characteristics predict when foundation models outperform simpler alternatives — moving beyond "model X beats model Y on dataset Z."
4. **Cost-accuracy Pareto analysis** with GPU hours, $/1000 series, and CO2 estimates — practical guidance absent from most benchmark papers.
5. **Practitioner decision framework** — a flowchart mapping data characteristics to recommended model family, directly actionable for retail forecasting teams.

## Positioning

**Primary target:** International Journal of Forecasting (IJF) — aligned with M-competition tradition, systematic reviews valued.

**Preprint:** arXiv for early visibility and community feedback.

**Blog:** Summary post on stacked-data blog for practitioner reach.

## Differentiation from Prior Work

| Work | What it does | What we add |
|------|-------------|-------------|
| GIFT-Eval (NeurIPS 2024) | Benchmarks 20 models on 28 datasets | Cost analysis, covariate comparison, meta-regression |
| fev-bench (2025) | 100 tasks with covariates + statistical rigor | Foundation model evaluation, retail-specific synthesis |
| M5 papers (2020-2022) | Retail demand on single dataset | Foundation models, cross-benchmark meta-analysis |
| Individual foundation model papers | Report results on selected benchmarks | Cross-model, cross-dataset systematic comparison with moderators |

**Key insight:** No existing work synthesizes results *across* benchmarks with meta-regression. Each paper reports its own results on its own datasets. We connect the dots.
