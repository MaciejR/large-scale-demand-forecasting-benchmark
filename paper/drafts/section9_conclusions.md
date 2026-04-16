# §9 Conclusions

We presented a PRISMA-compliant systematic review of foundation
models for retail demand forecasting, augmented with original
gap-filling experiments that fill a structural hole in the
literature: no existing paper reports both FM and gradient-boosted
tree results on the same retail dataset under matched conditions
(§4.4). The study synthesised 185 extraction rows from 38
studies (2020–2026) with 45 experiment rows across M5, Favorita,
and Rohlik v2 under a unified rolling-origin protocol.
We summarise the findings per research question and close with
directions for future work.

### 9.1 Answers to the research questions

**RQ1 (Accuracy): Do zero-shot foundation models outperform
gradient-boosted tree baselines on retail WAPE?**

No, not in general. The cross-paper pooled meta-regression on
k = 10 bucket-level deltas finds Δ̂(FM − ML_TREE) = +0.101 WAPE
(p = 0.505) on the full pool — a sign flip driven by proper
precision-weighting of the M5 WRMSSE bucket — and Δ̂ = −0.044
WAPE (p = 0.17, Q p = 0.85) after excluding M5. The confidence
interval on the excl-M5 estimate [−0.11, 0.03] includes zero
with negligible heterogeneity. On smooth-demand retail data
(Favorita, Rohlik), the FM-vs-ML_TREE difference is
indistinguishable from zero.

The M5 WAPE cells (Δ ≈ −0.54 to −0.78) show a large apparent FM
advantage, but this reverses on WRMSSE (Δ = +0.41) because per-
series WAPE on intermittent demand penalises tree models via
zero-denominator explosions. M5 is a dataset-specific finding
driven by metric sensitivity, not a family-level effect.

**RQ2 (Moderators): Which data characteristics moderate the
FM-vs-ML_TREE gap?**

Demand intermittency (H1) is the primary moderator: M5 (zero-day
fraction ~70%) is the only dataset where the FM-vs-ML_TREE sign
depends on metric choice, and it is the only dataset that generates
significant heterogeneity in the pool. Covariate richness (H2) is
direction-consistent: on Favorita, where covariates carry real
signal, lightgbm_cov matches the FM within 0.3 pp. The LightGBM
multi-step protocol (H3) is conditional on intermittency: direct
wins on M5 (intermittent) by 17–22%, recursive wins on Favorita
and Rohlik (smooth) by 3–10%, vindicating the §5.3.6 conditional
synthesis. The interaction term H4 is untestable at k = 10.

All moderator CIs are wide at the current pool size; we report
direction-consistency rather than CI-based significance tests and
flag this as the primary limitation of the current analysis.

**RQ3 (Cost): What is the cost-accuracy Pareto frontier?**

Consumer-hardware FM inference (MacBook M-series MPS) costs
~$0.003 per 1,000 series per horizon — 16× cheaper than Azure
E4DS_V4 batch baselines in USD. However, the Polish-grid CO₂
footprint is 44× higher per $ than the Swedish-hydro Azure grid,
and wall time is 4× slower. On smooth-demand data where FM and
LGBM accuracy are within 1 pp WAPE, the cost differential favours
the FM when no cloud budget exists and favours LGBM when cloud
infrastructure is already provisioned.

**RQ4 (Guidance): When should a retail team deploy a foundation
model?**

The §7 decision framework distils the findings into three
conditions where the FM pays off:

1. **No feature engineering capacity.** When the team cannot build
   or maintain a covariate pipeline, zero-shot FM inference on
   consumer hardware delivers competitive accuracy (<1 pp WAPE
   gap on smooth-demand data) with zero data preparation.

2. **Cold-start series.** For new SKUs with no sales history,
   zero-shot FMs produce reasonable forecasts from day one, while
   global LightGBM requires at least a partial training window.

3. **Aggregate-level forecasting on intermittent data.** When the
   business KPI is at the category or store level (not per-SKU),
   the aggregate WAPE of FMs on M5 (~0.85) is comparable to
   LGBM, and the FM avoids the per-series WAPE pathology entirely.

The FM does NOT pay off when: (a) the team has rich covariates and
the capacity to use them (LGBM matches or beats FM), (b) per-series
accuracy on intermittent demand matters (WRMSSE favours LGBM by
45 pp on M5), or (c) batch throughput at scale is the constraint
(LGBM on CPU is faster per series than FM on MPS for >10K series).

### 9.2 Future work

**Covariate-aware FM evaluation.** Chronos-2 (v2) and Moirai 2.0
support exogenous covariates. Running these models with promotions
and calendar features on Favorita and Rohlik would test whether the
covariate channel closes the FM-vs-LGBM gap on smooth-demand data.
This is the single highest-value extension of the current work.

**Larger cross-paper pool.** The k = 10 pool limits moderator
analysis to direction-consistency. As more FM papers report per-
series WAPE on individual retail datasets under rolling-origin
protocols, the pool will grow and enable CI-based moderator tests.
We encourage the community to report per-series and aggregate WAPE
alongside skill scores, and to include at least one tree-based
baseline in every retail FM evaluation.

**Probabilistic metrics.** CRPS, quantile loss, and calibration
error would complement the point-forecast WAPE analysis and may
reveal FM advantages in the tails of the predictive distribution
that WAPE cannot capture.

**Fine-tuned FM evaluation.** Our study is restricted to zero-shot
FMs. Lightweight fine-tuning (e.g., LoRA on Chronos-2 with 1% of
target data) could shift the FM-vs-ML_TREE balance, especially on
covariate-rich datasets where the FM's pre-trained features are
augmented with task-specific signal.

**Beyond retail.** The conditional finding (intermittency × metric
choice drives the FM-vs-ML_TREE comparison) should be tested on
spare-parts, pharmaceutical, and e-commerce demand datasets, which
span the full intermittency spectrum.
