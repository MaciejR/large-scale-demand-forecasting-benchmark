# Contributions and Positioning (v0.2 — updated 2026-04-16)

## Research Questions

- **RQ1:** Do time-series foundation models (zero-shot) outperform
  traditional ML models on retail demand forecasting tasks?
  **Answer (preliminary):** No, on smooth-demand retail datasets.
  Cross-paper Δ̂(FM − ML_TREE) = −0.044 WAPE (n.s., p = 0.17) on
  Favorita + Rohlik. M5 shows a large FM advantage on WAPE
  (Δ ≈ −0.54 to −0.78) but this reverses on WRMSSE (+0.41) and
  is driven by per-series metric pathology, not model quality.

- **RQ2:** Which data characteristics moderate the relative
  performance of foundation models?
  **Answer (preliminary):** Demand intermittency is the primary
  moderator (H1, direction-consistent). Covariate richness (H2)
  reduces FM advantage on Favorita; the LightGBM protocol (H3)
  is conditional on intermittency per §5.3.6. The cross-paper
  pool (k = 10) has insufficient power for CI-based gate tests;
  we report direction-consistency instead.

- **RQ3:** What is the cost-accuracy Pareto frontier across model
  families when compute cost and CO₂ are considered?
  **Answer (preliminary):** Consumer-HW (MacBook MPS) FM inference
  is 16× cheaper in $ than Azure E4DS_V4 batch but 44× higher in
  CO₂ (Polish grid) and 4× slower in wall time. On Favorita where
  FM and LGBM are within 0.3 pp WAPE, the cost differential
  determines the deployment recommendation.

- **RQ4:** Under what conditions should a retail practitioner
  choose a foundation model over LightGBM?
  **Answer (preliminary):** When the team lacks feature engineering
  capacity, faces cold-start series, or can tolerate ±1 pp WAPE
  relative to a well-tuned LightGBM with covariates. On datasets
  with >15% zero-day fraction, per-series WAPE makes the
  comparison unreliable — use aggregate WAPE or WRMSSE instead.

## Contributions

1. **First PRISMA-compliant systematic review** of foundation
   models for retail demand forecasting, synthesising 185
   extraction rows (2020–2026) across M5, Favorita, Rohlik v2,
   GIFT-Eval, and fev-bench — and documenting the structural gap
   that no existing paper reports both FM and ML_TREE on the same
   retail dataset under matched conditions (§4.4).

2. **Gap-filling experiments** (Source B, 45 rows): Chronos-Bolt-
   Tiny + TiRex on consumer hardware, LightGBM + seasonal_naive
   on Azure batch, all under a unified rolling-origin protocol
   with shared paper_id for within-paper pairing.

3. **Cross-paper pooled meta-regression** (k = 10 bucket-level
   deltas, metafor::rma.mv REML with Knapp-Hartung) identifying
   a null FM-vs-ML_TREE effect on smooth-demand retail (Δ̂ =
   −0.044, p = 0.17) and a M5-specific metric artefact.

4. **Baseline reliability analysis** (§5.3): the LightGBM
   direct-vs-recursive protocol gap is conditional on demand
   intermittency, not a universal protocol recommendation —
   vindicated by Source B across three datasets.

5. **Practitioner decision framework** (§7) mapping data
   characteristics to model family recommendations, with cost-
   accuracy Pareto figures for consumer-HW and cloud-GPU axes.

## Positioning

**Primary target:** International Journal of Forecasting (IJF) —
aligned with M-competition tradition, systematic reviews valued.

**Preprint:** arXiv for early visibility and community feedback.

**Blog:** Summary post on stacked-data blog for practitioner reach.

## Differentiation from Prior Work

| Work | What it does | What we add |
|------|-------------|-------------|
| GIFT-Eval (NeurIPS 2024) | 20 models on 28 datasets | Cost analysis, retail-specific WAPE caveat, meta-regression |
| fev-bench (2025) | 100 tasks with covariates | FM evaluation, cross-benchmark synthesis |
| M5 papers (2020–2022) | Retail demand on single dataset | FM models, per-series WAPE pathology analysis, cross-dataset meta-analysis |
| FM papers (2024–2026) | Report results on own benchmarks | Cross-model, cross-dataset, cross-metric synthesis with moderators |

**Key insight:** The FM-vs-ML_TREE gap is **null** on smooth-demand
retail data and **metric-dependent** on intermittent-demand data.
No prior work makes this distinction because no prior work runs the
same models on M5, Favorita, and Rohlik under matched conditions
and reports both per-series WAPE and aggregate WRMSSE on M5.
