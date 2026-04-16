# Appendix F: Threats to Validity — §5.4 Foundation Model Protocol

Five threats specific to the Source B foundation model runs (§5.4),
in decreasing order of magnitude:

1. **Extraction selection bias.** Papers that publish on M5 /
   Favorita / Rohlik are not a random sample of the FM
   literature — they are the subset that chose a retail task
   for their own evaluation. Papers that chose ETT / Weather /
   ECL (most of the LSF literature) are absent. The §6.6
   heterogeneity diagnostic includes a `paper_chose_retail_as_
   primary_task` binary flag to surface this.

2. **Source A vs Source B protocol drift.** Source A numbers
   are extracted as-reported; Source B numbers are run on our
   §5.1.3 protocol. When the two diverge on the same (model,
   dataset, horizon) cell, the divergence is a data point
   about protocol sensitivity, not about model quality. The
   three-model overlap between A and B is designed to quantify
   this drift, and §5.4.7 treats >5% gaps as findings.

3. **Local run is three small models only.** The four large
   models (Moirai 2.0, TimesFM 2.5, Chronos-2, Chronos-Bolt
   bigger variants) cannot be run locally and are therefore
   represented in Table 5.7 only by Source A. A reviewer who
   distrusts Source A on a specific large model cannot cross-
   check against our local run. We flag this as the single
   biggest residual risk in §7.

4. **Covariate asymmetry.** Four of the six FM families in
   Table 5.7 are univariate and cannot consume the §5.1.1
   covariate sets. The LightGBM baselines in §5.2 use the
   full covariate sets. This biases the comparison toward
   LightGBM on covariate-driven datasets (M5: SNAP, prices;
   Favorita: oil, promotions) and is not correctable inside a
   zero-shot protocol. §6.2 treats covariate-aware vs
   univariate as a moderator.

5. **Top-30k Favorita cap propagates to the local run.** Same
   cap, same selection rule, same velocity bias as §5.1.1.
   Source A rows for Favorita include both fev-bench's top-54k
   subset and the full-Favorita subset where available; we
   flag `dataset_variant` per row so the §6 pool can restrict
   to comparable subsets.
