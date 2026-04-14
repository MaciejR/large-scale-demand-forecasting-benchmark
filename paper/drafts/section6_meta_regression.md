# §6 Meta-Regression — DRAFT v0.1

*Drop-in draft for §6 of the paper. This section is the analytic
core of the meta-analysis. It combines the 25+ papers extracted in
§4 (see `analysis/extraction_schema.csv`, 214 rows at time of
writing) with our own gap-filling experiments (§5.2–§5.3) into a
single moderator-aware comparison of foundation models and
gradient-boosted-tree baselines on retail demand forecasting.
Our own FM rows come from two sources defined in §5.4: the
PRISMA literature extraction (Source A, primary) and a small
local consumer-box run on a MacBook (Source B, secondary,
scheduled 2026-04-15/16). §6.1–§6.5 all run on Source A alone
and do not block on Source B; Source B tightens the §6.5
Pareto frontier when it lands but does not change the main
findings. No cloud-GPU FM work is planned; the v0.1 Phase F
sweep has been dropped.*

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
**Our own Phase C/D/E LightGBM rows enter this pool immediately**
as a single (paper = ours, dataset ∈ {M5, Rohlik, Favorita},
horizon ∈ {7, 14, 28}) contribution per baseline variant, with
the LightGBM baseline being the per-dataset best variant from
§5.3.9 (direct on M5, recursive on Rohlik and Favorita). The
LOCAL FM rows from §5.4.3 enter the pool when the local run
completes, but Pass 1 is fully runnable on extraction + our
LightGBM rows alone.

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
the final extraction, scheduled for the Source B local-run
freeze in the week of 2026-04-20).

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
across three datasets on an Azure CPU node; §5.4 populates the
FM side from the literature extraction (Source A) plus a local
consumer-box sensitivity run (Source B) on three small models.
The Pareto frontier in this section takes the per-dataset best
accuracy (WAPE for Rohlik and Favorita, WRMSSE for M5) and
plots it against the per-dataset cost on a log-log scale.

**Figure 6.4 is framed on consumer hardware, not cloud GPU.**
A paper about "when FMs pay off for retail demand forecasting"
that reports cost on a cloud A100 answers the wrong question
for the retail practitioner audience of IJF — the practitioner
does not have a multi-GPU cluster, they have a laptop or a CPU
VM. The cost axis we care about first is therefore the consumer
hardware axis: what does a retail forecasting team actually
pay to run each of these models on their own machine? The
cloud-GPU version of the same plot lives in Figure 6.5 as a
sensitivity check for reviewers who prefer that reference point.

**Figure 6.4 [placeholder — primary: consumer-hardware Pareto].**
Cost-accuracy Pareto frontier across the three datasets (M5,
Rohlik v2, Favorita top-30k) on consumer hardware. X-axis:
log₁₀ USD of the full 9-job equivalent sweep per dataset per
family, priced at the consumer-CPU amortization of a $1,500
laptop running 24/7 (≈ $0.007/hr straight-line over 3 years).
Y-axis: the per-dataset WAPE / WRMSSE of the best variant. The
data for this figure comes from three sources:

- **LightGBM baselines (§5.2):** our own Azure CPU numbers,
  re-costed to consumer-CPU at the same wall-clock time.
  E4DS_V4 (4 vCPU) and a recent laptop are performance-
  comparable for the gradient-boosted tree workload; we verify
  this assumption on a single M5 direct-h=7 run during the
  local sweep of §5.4.3 and record the scaling factor in the
  figure caption.
- **Local FM sensitivity (§5.4.3, Source B):** our own 27-row
  local run for Chronos-Bolt-Tiny, TabPFN-TS, and TiRex on the
  three datasets × three horizons. These are the only data
  points on Figure 6.4 where both the accuracy number and the
  cost number come from the same machine — the tightest
  anchor the figure has.
- **Extracted consumer-HW FM numbers (§5.4.2, Source A):** F04
  (arXiv 2602.10848) publishes Chronos-Bolt-Tiny throughput on
  M-series laptops for an energy-load task, and we scale
  through to retail using its reported per-series-day rate.
  Chronos-2, TimesFM 2.5, Moirai 2.0, and the larger
  Chronos-Bolt variants are plotted using their source papers'
  reported wall-clock numbers on "comparable consumer HW"
  where such a number is published; where it is not, those
  models appear only on Figure 6.5.

The central claims Figure 6.4 tests:

- **On M5,** direct LightGBM at WRMSSE 0.56 is the accuracy
  winner and sits at a consumer-CPU cost of roughly $0.01 for
  a single 62-minute training (versus our Azure-CPU cost of
  $0.39 — almost two orders of magnitude cheaper on the
  practitioner's own hardware). A FM that wants to Pareto-
  improve on M5 must beat WRMSSE 0.56 *and* fit in the same
  cost class on the same hardware, which is a genuinely
  difficult bar for any model above ~30 M parameters.

- **On Rohlik,** recursive LightGBM at WAPE 0.365 and a
  consumer-CPU cost of under $0.001 (single-digit seconds of
  wall time) is an extreme cost floor. Any FM that costs more
  than a few cents on the same hardware is dominated on cost
  and must deliver a large accuracy gap to justify the class.
  Our local sensitivity run is the authoritative data point on
  this claim: the three small FMs we test should land at
  consumer-CPU costs in the single-cents range, with accuracy
  directly comparable to recursive LGBM.

- **On Favorita,** recursive LightGBM at WAPE 0.530 and
  consumer-CPU cost of a few cents is the cost floor. The
  direct LGBM variant at WAPE 0.551 and Azure cost $1.03 is a
  dominated point on Favorita even on Azure (§5.3.5) and more
  dominated on consumer CPU where it takes hours of laptop
  time. Favorita is the single most visually striking panel of
  Figure 6.4: the "standard" M5-era LightGBM protocol is
  dominated by a simpler, cheaper variant AND by the three
  small local FMs (if our local run confirms the A11/A13/A14
  published numbers).

**Figure 6.5 [placeholder — sensitivity: cloud-GPU Pareto].** The
same Pareto frontier re-costed on cloud GPU (single V100 at
$1.24/hr, the pricing class from §5.4.2 v0.1). Same X-axis
definition, same Y-axis, same models. The cost of every FM
point shifts ~10–100× rightward relative to Figure 6.4, and
the cost of every LightGBM point shifts roughly 3× rightward.
On this figure, some of the larger FMs (Chronos-2, Moirai 2.0,
TimesFM 2.5) that are not in Figure 6.4 become plottable
because cloud-GPU numbers for them are published in A02, A06,
and A04.

Figure 6.5 is the version a reviewer who "evaluates against
standard cloud GPU" would reach for; Figure 6.4 is the version
a retail practitioner with a laptop would reach for. Both are
honest; both appear in the paper. The reason Figure 6.4 is
primary and 6.5 is sensitivity — a reversal from v0.1 of this
draft — is that the IJF audience is the practitioner, and the
consumer-hardware cost floor is where the FM-beats-LightGBM
question is actually decided in practice.

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

3. **Our own results participate in the pool.** Phase C/D/E
   contribute LightGBM-baseline rows (`paper_id = OWN_*`) and
   §5.4.3 contributes three-model local FM rows (`paper_id =
   LOCAL_*`). To avoid double-counting our own experiments, we
   report the pooled Δ three ways: (i) full pool, (ii) excluding
   OWN_*, (iii) excluding both OWN_* and LOCAL_*. If
   conclusions flip across these three variants, the finding is
   that our own work is driving the meta-regression — a
   finding about the meta-analysis rather than about FMs — and
   we flag it in §7.

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
*before* the §5.4.3 local run lands. All four hypotheses are
testable against the Source A extraction alone today; Source B
tightens them when the local run freezes. The four load-bearing
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

All four hypotheses are testable against the Source A
extraction today and are re-tested against the Source A + B
union once the §5.4.3 local run lands. §6.7 reports the four
coefficients, CIs, and gate outcomes as a single table
(Table 6.3 placeholder) in the final draft, with a second
column showing the coefficient under the Source-A-only
restriction, so the reader can see whether LOCAL rows changed
any of the four conclusions.

---

*Sources for this section:* `analysis/extraction_schema.csv`
(Source A — 214 rows, 25+ papers at time of writing, grows to
~241 rows after the §5.4.3 LOCAL run lands), §5.3's three-
dataset synthesis, and the PRISMA screening record in
`analysis/prisma_search_protocol.md`. Code for the meta-
regression, forest plots, and heterogeneity diagnostics is in
`analysis/meta_regression.R` and `analysis/figures/` (to be
committed with the final extraction before paper submission).
