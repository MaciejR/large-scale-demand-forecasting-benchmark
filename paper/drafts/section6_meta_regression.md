# §6 Meta-Regression — DRAFT v0.1

*Drop-in draft for §6 of the paper. This section is the analytic
core of the meta-analysis. It combines the 25+ papers extracted in
§4 (see `analysis/extraction_schema.csv`, 214 rows at time of
writing) with our own gap-filling experiments (§5.2–§5.3) into a
single moderator-aware comparison of foundation models and
gradient-boosted-tree baselines on retail demand forecasting.
Phase F (our own FM rows) feeds §6.1 and §6.3 when it lands;
§6.2, §6.4, and §6.5 depend only on the existing PRISMA extraction
and are fully runnable now.*

---

### 6.1 Pooling strategy and effect size

The PRISMA corpus (§4) reports results in heterogeneous forms:
WAPE, MAE, sMAPE, WRMSSE, CRPS, MASE, and scaled quantile losses
(WQL). No single pooled effect is defensible across this mix;
instead we use three pooling passes, each at a different level of
strictness, and cross-reference the conclusions in §6.6.

**Pass 1 — Dataset-anchored pooled relative error (primary).** For
each (paper, dataset, horizon) cell in the extraction table, we
compute a single "relative error vs the paper's own best
non-FM baseline" statistic:

```
Δ_{p, d, h} = (metric_FM - metric_LGBM) / metric_LGBM
```

where `metric_LGBM` is whichever LightGBM, XGBoost, or Tree-based
ensemble variant the paper itself reports (if any); if the paper
reports multiple, we use the paper's strongest. The sign is
oriented so negative values mean "FM beats baseline". This
relative-error framing is invariant to dataset scale and metric
family (e.g. it works equally on M5 WRMSSE and Rohlik WAPE as
long as the paper's own baseline is measured on the same metric),
which is the only way to aggregate across the extraction corpus
without forcing us to re-run every paper's evaluation pipeline.
**Our own Phase C/D/E rows enter this pool as a single
(paper = ours, dataset ∈ {M5, Rohlik, Favorita}, horizon ∈ {7, 14,
28}) contribution per FM once Phase F lands**, with the LightGBM
baseline being the per-dataset best variant from §5.3.9 (direct
on M5, recursive on Rohlik and Favorita).

**Pass 2 — Absolute metric on matched benchmarks.** Where multiple
papers report on the same benchmark × horizon × metric cell (e.g.
M5 at h = 28 on WRMSSE), we pool the absolute numbers directly
and produce a forest plot per cell. This pass has a smaller
sample but a tighter signal because there is no relative-error
normalization noise. M5 and Favorita are the two benchmarks with
enough coverage for a meaningful per-cell forest plot (§6.3).

**Pass 3 — Ordinal rank-in-paper.** For papers that report 5+
baselines on the same dataset × horizon, we extract the rank of
each method inside that paper's own table. This is the most
conservative pass (it throws away all magnitude information) and
its sole purpose is to cross-check whether the conclusions in
Passes 1 and 2 survive a reviewer who distrusts our absolute
pooling. Rank pooling is a standard robustness check in
meta-analysis; we use Friedman's test and the Nemenyi post-hoc
comparison (Demšar 2006) as the numerical summary.

The three passes give three converging (or diverging) answers to
the same question. If they converge, the meta-regression claims
are robust; if they diverge, we report the divergence as a
moderator-interaction finding in §6.6.

### 6.2 Moderator variables

The extraction schema records 22 columns per row; eight of those
are moderator variables that the meta-regression explicitly
tests for interactions with the FM-vs-LGBM effect. The eight
moderators and our a-priori hypothesis on the sign of each
interaction:

| Moderator | Definition | Hypothesis (FM advantage) |
|---|---|---|
| `zero_day_fraction` | Fraction of series-day observations with `y = 0` | Decreases with intermittency (FMs under-fit zeros) |
| `n_series` | Number of distinct series in the benchmark | Increases with scale (FMs benefit from per-series capacity) |
| `covariate_rich` | Binary: does the dataset ship with ≥3 covariates used by the baseline? | Decreases when true (baselines use covariates, most FMs cannot) |
| `protocol_direct` | Binary: is the LightGBM baseline direct-multistep rather than recursive? | Decreases when true (direct is the stronger LGBM variant) |
| `horizon` | Forecast horizon in days | Ambiguous: FMs good at long, but so is LGBM-direct |
| `fine_tuned` | Binary: was the FM fine-tuned on the target dataset? | Increases strongly when true (removes zero-shot penalty) |
| `model_family` | Chronos / TimesFM / Moirai / TTM / TabPFN / other | Categorical control, not a-priori signed |
| `pub_year` | Year of publication | Increases with year (newer FMs are better) |

The meta-regression in §6.4 runs a mixed-effects model with
`Δ` as the outcome, `paper_id` as the random effect (to control
for within-paper clustering of multiple rows), and the eight
moderators as fixed effects. Following Viechtbauer (2010) and
the `metafor` R package convention, we use a restricted maximum
likelihood (REML) estimator with Knapp-Hartung adjustment for
small-sample degrees of freedom. All model specifications and
code are in `analysis/meta_regression.R` (to be committed with
the final extraction when Phase F lands).

### 6.3 Forest plots by benchmark × horizon

Two benchmarks in the extraction corpus have sufficient coverage
to produce useful forest plots: **M5** (daily, 30,490 series,
~70% zeros, 11 papers reporting at h ∈ {7, 14, 28}) and
**Favorita** (daily, ~54k series in the GIFT-Eval / fev-bench
subset, 7 papers reporting at h ∈ {7, 14, 28, 56}). Rohlik is
newly added to fev-bench (2025) and has only 2 external papers
reporting plus our own Phase D run, which is insufficient for a
forest plot but enters the pooled estimate of §6.4.

**Figure 6.1 [placeholder].** Forest plot of FM-vs-best-non-FM
relative error on M5 at `h = 28`. Each row is a (paper,
FM-family) cell from the extraction; the horizontal axis is Δ
with negative = FM beats LGBM. Rows are ordered by FM family
(Chronos variants, TimesFM variants, Moirai variants, TTM, other)
and within family by pub year. Our own Phase C M5 row (best
LGBM = direct h = 28, WRMSSE 0.599) anchors the right edge of
the plot as the stronger-baseline reference. The plot is
generated by `analysis/figures/fig6_1_forest_m5_h28.R` when the
extraction is frozen.

**Figure 6.2 [placeholder].** Same, on Favorita at `h = 28`. The
Favorita plot is visually different from M5 in one important way:
our own Phase E row has LGBM-recursive as the winner, so the
reference line is on the recursive side, and FM papers that
beat recursive LGBM on Favorita are *not* the same papers that
beat direct LGBM on M5. This visual effect is exactly the
cross-dataset protocol inversion of §5.3.6, and is the central
illustration of why the "LightGBM baseline" is a moderator, not
a main effect.

**Figure 6.3 [placeholder].** Pooled estimate across all
benchmarks, from Pass 1. Mixed-effects REML model from §6.2 with
the eight moderators. The main effect `β₀` is the grand-mean
FM-vs-LGBM relative improvement; we expect it to be close to
zero with substantial heterogeneity (I² > 75 %). The moderator
coefficients `β₁...β₈` and their 95% CIs are the main finding
of the meta-regression — the sign, magnitude, and CI of
`β_{zero_day_fraction}`, `β_{protocol_direct}`, and
`β_{covariate_rich}` are the three key numbers the reader should
take away from §6. Pre-registered hypotheses: all three are
negative (FMs lose when zeros are high, when the LGBM is direct,
and when covariates are used), and the `zero_day_fraction ×
protocol_direct` interaction is positive (direct LGBM's M5
advantage is specifically driven by zeros + direct together,
not by either alone).

### 6.4 The intermittency × protocol interaction

The single most important finding of the meta-regression, and
the one that best ties the extraction to our own experiments
(§5.3.6), is the interaction between `zero_day_fraction` and
`protocol_direct`. The extraction table covers this interaction
by stratifying our own rows and re-extracting the LightGBM
protocol explicitly for every indexed paper that compared against
a tree baseline. Our a-priori prediction (from §5.3.2 + §5.3.6)
is that the interaction term is strictly positive — i.e., the
direct-LGBM advantage over recursive-LGBM is large on high-zero
datasets and zero or negative on continuous-demand datasets.

The prediction is sharpened by the fact that the extraction
corpus disagrees with itself on this point across papers. C04
(Makridakis-style retail ML comparison, 2025) reports on a
continuous-demand retail dataset that recursive LGBM is the
stronger baseline, consistent with our Phase D and E. C01 (M5
competition retrospective, Makridakis et al. 2022) reports the
direct-dominates-recursive pattern on M5, consistent with our
Phase C. B01 (GIFT-Eval 2025) uses direct LGBM everywhere as
the default and does not report the inversion. **The
meta-regression treats this disagreement as a between-paper
heterogeneity to be explained by the zero-day fraction
moderator**, not a contradiction to be resolved by voting.

If the interaction coefficient is positive and the 95% CI does
not cross zero, the finding is that the protocol gap is a
function of the dataset, not a property of multi-step
LightGBM — which is §5.3.6 in meta-analytic form. If the
interaction CI crosses zero, the finding is that our three
datasets were special cases and we cannot generalize to the
full retail forecasting space without adding more continuous-
demand benchmarks; this would be the single most important
limitation of the paper and we would state it as such in §7.

**Table 6.1 [placeholder].** Mixed-effects meta-regression on
all extracted (paper × dataset × horizon) rows. Outcome: `Δ =
(FM - baseline) / baseline` for any metric the paper itself
reports. Sample size is the total number of rows where we have
both an FM number and a matched baseline number (estimated at
~180 rows from the current extraction; exact count when Phase
F lands). Columns: moderator name, coefficient, standard error,
t-value, df, p-value, 95% CI. Hypotheses pre-registered above.
The table is generated by `analysis/meta_regression.R`.

### 6.5 Cost-accuracy Pareto frontier

The cost axis is the second main finding of §6. §5.2.3 and
§5.3.8 showed that the baseline LightGBM sweep costs $2.05
across three datasets on a CPU node; §5.4.5 projects the
zero-shot FM sweep at $18–24 on a GPU node. The Pareto frontier
in this section takes the per-dataset best accuracy (WAPE for
Rohlik and Favorita, WRMSSE for M5) and plots it against the
per-dataset sweep cost on a log-log scale.

**Figure 6.4 [placeholder].** Cost-accuracy Pareto frontier
across the three datasets (M5, Rohlik v2, Favorita top-30k).
X-axis: log₁₀ USD of the full 9-job sweep per dataset per
family. Y-axis: the per-dataset WAPE / WRMSSE of the best
variant. Three Pareto-front candidates are marked: Seasonal
Naive (cost floor), best-per-dataset LightGBM, and best-per-
dataset zero-shot FM (pending Phase F). The central claim the
figure tests is:

- **On M5**, direct LightGBM at WRMSSE 0.56 and cost $0.57 is
  the cost floor for competitive accuracy. A FM that reports
  WRMSSE ≤ 0.56 on M5 at cost > $0.57 is dominated on cost but
  not on accuracy (standard Pareto); a FM that reports WRMSSE
  > 0.56 on M5 is dominated on both axes. The space for a FM
  to Pareto-improve on M5 is therefore "match WRMSSE ≤ 0.56 at
  cost ≤ $0.57 and accept licensing / deployability asymmetry".

- **On Rohlik**, recursive LightGBM at WAPE 0.365 and cost
  $0.009 is an extreme cost floor. Any FM that costs more than
  $0.01 per 9-job sweep is dominated on cost and must
  Pareto-improve on accuracy by a large margin to justify its
  cost class. At the projected $4–8 per-FM cost on Rohlik from
  §5.4.5, the required accuracy gap is enormous.

- **On Favorita**, recursive LightGBM at WAPE 0.530 and cost
  $0.073 is the cost floor. The direct LGBM variant at WAPE
  0.551 and cost $1.03 is a dominated point on Favorita —
  strictly worse on both axes than recursive. This is the
  single most visually striking panel of Figure 6.4, because
  it demonstrates that the "standard" LightGBM protocol from
  the M5 literature is dominated on a different retail dataset
  by a simpler protocol that costs 14× less.

The Pareto analysis is conditional on the GPU cluster pricing
we use (§5.4.2). A FM paper that runs on a CPU-only consumer
box (F04, energy load, 2026; cites throughput of ~100
series-day/s for Chronos-Bolt-Tiny on an M-series laptop) would
shift the FM points leftward on the Figure 6.4 X-axis by
roughly 10×. We therefore report the Pareto frontier twice:
once on our own GPU cluster pricing (primary) and once on F04's
reported consumer-CPU-box pricing (sensitivity, Figure 6.5
placeholder). The sensitivity version is the one a retail
practitioner with a laptop would care about; the primary
version is the one a reviewer who evaluates against "standard
cloud GPU" would care about. Both are honest.

### 6.6 Heterogeneity, threats, and disagreement with the extraction

Three sources of heterogeneity are large enough to deserve
explicit treatment:

1. **Metric family.** The extraction corpus mixes WAPE, WRMSSE,
   MAE, CRPS, MASE, and WQL. Pass 1 of §6.1 handles this by
   normalizing each paper's Δ against its own baseline on its
   own metric, but this is only defensible if within-paper
   metrics are monotone in "true quality". For sMAPE the
   monotonicity is badly violated on retail data (§5.3.2 and
   §5.3.5) and we exclude sMAPE from the primary pool.

2. **Baseline definition.** A paper that reports "LightGBM
   baseline" without stating protocol, features, training
   window, and tree count is recorded in the extraction with a
   `baseline_quality_tier ∈ {weak, standard, strong}` rating
   based on the three-dataset ceiling in §5.3.3 and §5.3.9.
   Weak-baseline rows are flagged and their Δ is inflated by
   the expected over-reporting bias; the inflation factor is
   in Table 5.3's gap column (M5 direct vs recursive is the
   "standard → strong" delta). When we run the meta-regression
   we include `baseline_quality_tier` as a moderator and report
   the pooled Δ both with and without the weak rows.

3. **Our own results participate in the pool.** Phase C/D/E/F
   contribute rows to the extraction (`paper_id = OWN_*`). To
   avoid double-counting our own experiments, we report the
   pooled Δ once *including* our rows and once *excluding*
   them, in the same table. If the conclusions flip between
   "include" and "exclude", the finding is that our own work is
   driving the meta-regression — which is a finding about the
   meta-analysis, not about FMs, and we flag it in §7.

**Table 6.2 [placeholder].** Heterogeneity diagnostics for the
primary mixed-effects model of §6.4. I² (heterogeneity not
explained by sampling error), τ² (between-study variance in Δ),
Q (Cochran's heterogeneity statistic), and a subgroup
decomposition of I² by `dataset_family ∈ {M5, Favorita, Rohlik,
other retail, cross-domain}`. The prediction from §5.3.6 is that
the heterogeneity decomposes largely into a between-dataset
component and a small within-dataset residual — i.e., most of
the FM-vs-LGBM variance in the literature is because people
report on different datasets with different intermittency, not
because FMs vary wildly in quality on a fixed dataset.

### 6.7 What §6 will conclude (hypotheses and gates)

§6 is a pre-registered meta-regression in the sense that §6.2
and §6.4 above state the sign of each moderator hypothesis
*before* the data from Phase F lands. The four load-bearing
hypotheses, with their prediction and gate criterion:

1. **H1 (intermittency ↓ FM advantage).** Coefficient on
   `zero_day_fraction` in §6.4 is **negative** with 95% CI
   excluding zero. Gate: if the CI includes zero, we weaken the
   headline claim from "FMs lose on intermittent retail" to
   "FMs do not consistently win on intermittent retail, and the
   literature is currently underpowered to detect the effect".

2. **H2 (covariates ↓ FM advantage).** Coefficient on
   `covariate_rich` is **negative** with 95% CI excluding zero.
   Gate: same as H1 on CI inclusion of zero.

3. **H3 (direct LGBM ↓ FM advantage).** Coefficient on
   `protocol_direct` is **negative**. This is the §5.3
   finding in meta-analytic form. Gate: if positive or
   CI includes zero, we report that the §5.3 cross-dataset
   finding does not replicate across the indexed literature,
   and we revise §5.3.6 accordingly before final submission.

4. **H4 (zeros × protocol interaction > 0).** Interaction
   coefficient on `zero_day_fraction * protocol_direct` is
   **positive** with 95% CI excluding zero. This is the
   cleanest test of the §5.3.6 synthesis. Gate: if positive,
   the paper's main claim is robust; if CI includes zero, the
   main claim weakens to "consistent on our three datasets, not
   yet generalizable".

All four hypotheses are testable against the existing extraction
and will be testable against the Phase F-extended extraction.
§6.7 will report the four coefficients, CIs, and gate outcomes
as a single table (Table 6.3 placeholder) in the final draft.

---

*Sources for this section:* `analysis/extraction_schema.csv`
(214 rows, 25+ papers at time of writing, will be 250+ after
Phase F), §5.3's three-dataset synthesis, and the PRISMA
screening record in `analysis/prisma_search_protocol.md`. Code
for the meta-regression, forest plots, and heterogeneity
diagnostics is in `analysis/meta_regression.R` and
`analysis/figures/` (to be committed with the final extraction
before paper submission).
