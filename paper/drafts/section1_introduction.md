# §1 Introduction (v0.1 draft — 2026-04-16)

The 2024–2026 wave of time-series foundation models — Chronos-2
(Ansari et al., 2025), TimesFM 2.5 (Das et al., 2025), Moirai 2.0
(Woo et al., 2025), TiRex (Gruber et al., 2025) — has shifted the
default assumption in short-term forecasting. Where a retail team
in 2022 would start with LightGBM and a feature-engineering sprint,
the 2026 playbook increasingly says: try a zero-shot foundation
model first, tune LightGBM only if the FM disappoints. Each model
paper reports favourable results on its own evaluation suite —
GIFT-Eval, fev-bench, or a curated subset of the M competitions —
but no paper runs the same battery of models under matched
conditions on the same retail datasets and reports the delta. The
benchmarks multiply; the synthesis does not.

This paper asks: **when do foundation models actually pay off for
retail demand forecasting?** We operationalise "pay off" as a
statistically significant reduction in per-series WAPE relative to
a well-tuned, covariate-aware LightGBM baseline under a matched
rolling-origin protocol. By "when" we mean: on which datasets,
horizons, demand distributions, and hardware budgets.

### 1.1 Research questions

We address four research questions across three complementary lenses
(accuracy, moderators, and cost):

- **RQ1 (Accuracy):** Do zero-shot foundation models outperform
  gradient-boosted tree baselines on retail WAPE? (§6.7)
- **RQ2 (Moderators):** Which data characteristics — demand
  intermittency, covariate richness, forecast horizon, multi-step
  protocol — moderate the FM-vs-ML_TREE gap? (§6.8)
- **RQ3 (Cost):** What is the cost-accuracy Pareto frontier when
  consumer-hardware electricity, cloud-GPU list price, and CO₂
  footprint are included? (§6.5)
- **RQ4 (Guidance):** Under what conditions should a retail
  forecasting team deploy a foundation model instead of investing
  in feature engineering for LightGBM? (§7)

### 1.2 Approach

We follow a two-source PRISMA-compliant protocol:

1. **Source A (literature extraction).** We screen ~150 papers
   (2020–2026) from Scopus, Google Scholar, Semantic Scholar, and
   arXiv, applying retail-domain inclusion criteria (>1,000 series,
   quantitative accuracy metric on at least one of M5, Favorita,
   Rohlik v2, GIFT-Eval retail tasks, fev-bench retail tasks, or
   Walmart). The extraction yields 185 rows in a structured CSV
   with 23 fields per row (§3.2).

2. **Source B (gap-filling experiments).** Where model–dataset–
   horizon combinations are missing from Source A, we run our own
   experiments under a unified evaluation protocol (§5.1): two
   foundation models (Chronos-Bolt-Tiny, TiRex) on a consumer
   MacBook (Apple silicon MPS), and three baselines
   (lightgbm_cov, lightgbm_direct, seasonal_naive) on an Azure ML
   batch cluster. Source B produces 45 rows with runtime, cost,
   and CO₂ metadata, keyed to Source A via a shared paper_id
   scheme that enables within-paper and cross-paper meta-analytic
   pairing (§6.1).

The meta-regression (§6) pools Source A and Source B into a
cross-paper design: for each (dataset, horizon, metric) bucket,
we compute mean(FM rows) − mean(ML_TREE rows) as a single
bucket-level delta, then fit a random-effects model
(metafor::rma.mv, REML, Knapp-Hartung) with k = 10 buckets
clustered on dataset. This is the primary estimand of the paper.

### 1.3 Headline findings

Three findings motivate the sections that follow:

1. **The FM advantage is null on smooth-demand retail data.**
   Excluding M5, the cross-paper pooled delta is Δ̂ = −0.044 WAPE
   (95 % CI [−0.15, 0.06], p = 0.33). On Favorita, LightGBM
   with covariates matches Chronos-Bolt-Tiny within 0.3 pp at
   h = 7 — a marginal LGBM win. On Rohlik, FMs lead by 4–8 pp
   but the gap narrows with horizon and does not reach statistical
   significance in the meta-regression. The heterogeneity across
   the six excl-M5 buckets collapses to zero (Q p = 0.99),
   meaning the null result is not masking opposing effects.

2. **M5 is a dataset-specific finding, not a family-level effect.**
   The M5 WAPE cells show FM advantages of 54–78 pp over
   lightgbm_cov, but this is driven by a per-series WAPE
   denominator pathology on intermittent demand: several Azure
   lightgbm_cov runs logged WAPE_mean = ∞ (zero-denominator
   explosion on tail series). On the same M5 data using WRMSSE
   (the M5 competition metric), the sign reverses: competition-
   grade LightGBM scores 0.52 WRMSSE vs Chronos at 0.97. **The
   M5 WAPE and WRMSSE cells should not be averaged into a single
   "M5 effect."** The paper reports them as separate rows in
   Table 6.1 with an explicit metric caveat.

3. **The LightGBM protocol gap is conditional on intermittency.**
   §5.3.6 shows that the direct-vs-recursive multi-step gap flips
   sign at the continuous-demand boundary: direct wins on M5
   (intermittent) by 17–22 %, recursive wins on Favorita and
   Rohlik (smooth) by 3–10 %. This conditional pattern, confirmed
   by Source B gap-filling, means that no retail-benchmark protocol
   recommendation that ignores demand distribution can survive
   cross-dataset replication.

### 1.4 Contributions

1. **First PRISMA-compliant systematic review** of foundation
   models for retail demand forecasting (185 extraction rows,
   2020–2026).
2. **Gap-filling experiments** (45 rows) under a unified
   rolling-origin protocol with consumer-HW and cloud cost
   metadata.
3. **Cross-paper pooled meta-regression** identifying a null
   FM-vs-ML_TREE effect on smooth-demand retail and a metric-
   dependent M5 artefact.
4. **Baseline reliability analysis** documenting the conditional
   direct-vs-recursive LightGBM gap across three datasets.
5. **Practitioner decision framework** mapping data
   characteristics to model-family recommendations with cost-
   accuracy Pareto figures.

### 1.5 Paper structure

§2 surveys the forecasting taxonomy and existing benchmarks. §3
describes the PRISMA search protocol, extraction schema, and gap-
filling experimental design. §4 reports the literature extraction
results (PRISMA flow, descriptive statistics). §5 presents the gap-
filling experiments: §5.1–5.2 experimental setup and per-dataset
results, §5.3 baseline reliability (direct vs recursive), §5.4
foundation model consumer-box results. §6 runs the meta-regression:
cross-paper pooled deltas (§6.1), moderator hypotheses (§6.2–6.4),
cost-accuracy Pareto frontier (§6.5), heterogeneity diagnostics
(§6.6), and preliminary findings (§6.7). §7 translates the findings
into a practitioner decision framework. §8 discusses limitations
(k = 10 pool, metric sensitivity, consumer-HW-only Source B). §9
concludes with per-RQ answers and future work.
