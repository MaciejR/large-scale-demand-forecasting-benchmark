# Contributions and Positioning

This work makes the following contributions:

1. **A contemporary, multi-dataset benchmark** comparing statistical, ML, deep learning, and foundation models for short-term demand forecasting across M5, GIFT-Eval (sales), and fev-bench — the first benchmark to unify these three sources under one protocol.
2. **Foundation model reality check:** An empirical assessment of whether Chronos-2, TimesFM 2.5, and Moirai 2.0 (zero-shot and fine-tuned) outperform simpler models when computational cost is factored in.
3. **Covariate-aware evaluation:** Leveraging fev-bench's 46 covariate tasks to quantify the accuracy gap between univariate foundation models and covariate-aware ML approaches — a gap largely absent from existing benchmarks.
4. **Cost–accuracy Pareto analysis** with GPU hours, wall-clock time, and CO₂ estimates — practical guidance for retail practitioners choosing between model complexity and operational cost.
5. **Full reproducibility:** All experiments tracked via MLflow on Azure ML, with YAML pipeline definitions, versioned data assets, and published code.

## Positioning
The paper targets applied forecasting and operations research venues:
- **International Journal of Forecasting (IJF)** — primary target, aligned with M-competition tradition
- **European Journal of Operational Research (EJOR)** — cost-accuracy trade-off angle
- **NeurIPS / ICML Datasets and Benchmarks track** — if foundation model analysis is the lead narrative

## Differentiation from Prior Work
- GIFT-Eval (2024) benchmarks foundation models but does not include cost analysis or covariate comparison
- fev-bench (2025) provides statistical rigor but focuses on library integration, not retail-specific insights
- M5 papers (2020–2022) predate foundation models entirely
- This work bridges all three: **retail focus + foundation models + covariates + cost**
