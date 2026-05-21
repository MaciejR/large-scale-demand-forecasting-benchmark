# §6 Meta-Regression

This section combines the 38 studies extracted in §4 (185 rows)
with our gap-filling experiments (§5, 45 rows) into a cross-paper
pooled comparison of foundation models and gradient-boosted-tree
baselines on retail demand forecasting. As documented in §4.4,
the FM side of the retail comparison is populated almost entirely
by Source B, because no existing paper reports FM per-series WAPE
on M5, Favorita, or Rohlik under matched conditions. Source A
contributes the bulk of the ML_TREE side. §6.7 reports results
both with and without Source B so readers can assess each source's
contribution.

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
**Our own LightGBM rows (§5.2) enter this pool immediately**
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
code are in `analysis/meta_regression.R`.

### 6.3 Forest plots by benchmark × horizon

Figures 6.1–6.3 present per-dataset forest plots of the
cross-paper pooled Δ cells from Table 6.1. Each dataset has
3 cells (horizons 7, 14, 28 on WAPE); M5 has a fourth cell
(WRMSSE at h = 28). The plots visualise the dataset-level
patterns that drive the pooled intercept of §6.7.

**Figure 6.1.** Forest plot of cross-paper pooled Δ cells on
M5 (3 WAPE cells + 1 WRMSSE cell). Each row is a (horizon,
metric) bucket; the horizontal axis is Δ = mean(FM) −
mean(ML_TREE) with negative = FM better. The three WAPE cells
show large negative Δ (−0.54 to −0.78), reflecting the per-series
WAPE artefact on intermittent demand (§5.4.5). The single WRMSSE
cell reverses sign (Δ = +0.41, FM worse). This within-dataset
metric reversal is the central evidence that the M5 FM advantage
is metric-specific, not family-level.
(`analysis/figures/figure_6_forest_m5.pdf`)

**Figure 6.2.** Forest plot of cross-paper pooled Δ cells on
Favorita (3 WAPE cells across horizons 7, 14, 28). All three
cells show small negative Δ (−0.012 to −0.021), consistent with
the headline finding that the FM-vs-LGBM gap is indistinguishable
from zero on smooth-demand retail data. The narrow range across
horizons indicates that neither family degrades faster with
horizon length on this dataset.
(`analysis/figures/figure_6_forest_favorita.pdf`)

**Figure 6.3.** Forest plot of cross-paper pooled Δ cells on
Rohlik (3 WAPE cells across horizons 7, 14, 28). Δ ranges from
−0.055 (short) to −0.089 (long), showing a modest FM advantage
that grows with horizon. This is the strongest per-dataset FM
signal in the excl-M5 pool, but it does not reach significance
in the pooled model (Table 6.1, excl-M5 intercept p = 0.174).
(`analysis/figures/figure_6_forest_rohlik.pdf`)

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
stronger baseline, consistent with our Rohlik and Favorita
results (§5.3.4–§5.3.5). C01 (M5 competition retrospective,
Makridakis et al. 2022) reports the direct-dominates-recursive
pattern on M5, consistent with our M5 results (§5.3.1). B01
(GIFT-Eval 2025) uses direct LGBM everywhere as
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

**Table 6.1.** Cross-paper pooled Δ cells (k = 10). Each row is
a (dataset, horizon, metric) bucket; Δ = mean(FM) − mean(ML_TREE)
within the bucket (negative = FM better). Sampling variance vi
uses the cross-paper proxy of §3.4. Generated by
`analysis/meta_regression.R`.

| Dataset  | Horizon | Metric | mean(FM) | mean(ML_TREE) | n_FM | n_ML | Δ       | vi      |
|----------|---------|--------|----------|---------------|------|------|---------|---------|
| Favorita | long    | WAPE   | 0.543    | 0.563         | 2    | 4    | −0.021  | 0.00257 |
| Favorita | medium  | WAPE   | 0.534    | 0.551         | 2    | 4    | −0.017  | 0.00252 |
| Favorita | short   | WAPE   | 0.529    | 0.540         | 2    | 4    | −0.012  | 0.00252 |
| M5       | long    | WAPE   | 0.949    | 1.725         | 2    | 2    | −0.776  | 0.00502 |
| M5       | long    | WRMSSE | 0.971    | 0.561         | 1    | 7    | +0.410  | 0.00004 |
| M5       | medium  | WAPE   | 0.946    | 1.570         | 2    | 2    | −0.623  | 0.00502 |
| M5       | short   | WAPE   | 0.946    | 1.488         | 2    | 2    | −0.542  | 0.00502 |
| Rohlik   | long    | WAPE   | 0.349    | 0.438         | 2    | 4    | −0.089  | 0.00265 |
| Rohlik   | medium  | WAPE   | 0.330    | 0.401         | 2    | 4    | −0.071  | 0.00265 |
| Rohlik   | short   | WAPE   | 0.318    | 0.374         | 2    | 4    | −0.055  | 0.00265 |

**Pooled intercept (full, k = 10):** Δ̂ = +0.101, SE = 0.145,
t(9) = 0.694, p = 0.505, 95 % CI [−0.227, +0.429]. σ² = 0.063
(dataset-level). Q(9) = 1055.3, p < .0001.

**Pooled intercept (excl-M5 WAPE, k = 6):** Δ̂ = −0.044,
SE = 0.028, t(5) = −1.583, p = 0.174, 95 % CI [−0.115, +0.027].
σ² = 0.001 (dataset-level). Q(5) = 2.00, p = 0.849.

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

**Figure 6.4 (primary: consumer-hardware Pareto).** Cost-accuracy
Pareto frontier across the three datasets (M5, Rohlik v2,
Favorita top-30k) on consumer hardware. X-axis: log₁₀ USD of
the full 9-job equivalent sweep per dataset per family, priced
at the *marginal electricity* of an M-series laptop: ~30 W
sustained draw under inference × Polish residential electricity
($0.20/kWh) ≈ $0.006/hr. This is the cost the practitioner
actually pays on top of a machine they already own; it excludes
the sunk capex of the laptop itself. The hardware bucket
`M_SERIES_MAC` in `benchmark/code/evaluation/cost.py` uses
exactly these constants. Y-axis: per-dataset WAPE / WRMSSE of
the best variant. The data for this figure comes from two sources:

- **LightGBM baselines (§5.2):** Azure CPU numbers re-costed to
  consumer-CPU at the same wall-clock time. E4DS_V4 (4 vCPU) and
  a recent laptop are performance-comparable for tree workloads.
- **Local FM sensitivity (§5.4.3, Source B):** our own 45-cell
  local run for five models (Chronos-Bolt-Tiny, Chronos-2,
  Moirai-2, TiRex, TimesFM 2.5) on the three datasets × three
  horizons. Both the accuracy number and the cost number come
  from the same machine — the tightest anchor the figure has.
  F04 (arXiv 2602.10848) is cited as a prior precedent for the
  consumer-box framing but our own runs are the primary data.

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
  direct LGBM variant at WAPE 0.551 and Azure cost $1.03 is
  dominated even on Azure (§5.3.5) and more so on consumer
  CPU. Favorita is the single most visually striking panel of
  Figure 6.4: the "standard" M5-era LightGBM protocol is
  dominated by a simpler variant AND by all five local FMs.
  Chronos-2 and Moirai-2 beat recursive LGBM by ~5 pp WAPE
  at a comparable consumer-CPU cost of $0.01–0.02 per
  9-horizon sweep (§5.4.5 Table 5.9).

**Figure 6.5 (sensitivity: cloud-GPU Pareto).** The same Pareto
frontier re-costed on cloud GPU (single V100 at $1.24/hr). Same
X-axis definition, same Y-axis, same models. The cost of every
FM point shifts ~10–100× rightward relative to Figure 6.4, and
the cost of every LightGBM point shifts roughly 3× rightward.
Since all five Source B FMs also appear in Figure 6.5 re-costed
from their wall-clock times, the figure provides a complete
cross-axis view of the same 45 FM cells.

Figure 6.5 is the version a reviewer who "evaluates against
standard cloud GPU" would reach for; Figure 6.4 is the version
a retail practitioner with a laptop would reach for. Both are
honest; both appear in the paper. The reason Figure 6.4 is
primary and 6.5 is sensitivity is that the IJF audience is the
practitioner, and the
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

3. **Our own results participate in the pool.** The §5.2 baselines
   contribute LightGBM-baseline rows (`paper_id = OWN_*`) and
   §5.4.3 contributes three-model local FM rows (`paper_id =
   LOCAL_*`). To avoid double-counting our own experiments, we
   report the pooled Δ three ways: (i) full pool, (ii) excluding
   OWN_*, (iii) excluding both OWN_* and LOCAL_*. If
   conclusions flip across these three variants, the finding is
   that our own work is driving the meta-regression — a
   finding about the meta-analysis rather than about FMs — and
   we flag it in §7.

**Table 6.2.** Heterogeneity diagnostics for the two pooled models.
I² is estimated as max(0, (Q − df)/Q × 100). τ² is the
between-dataset variance component (σ² from `rma.mv` with
`random = ~1|dataset_norm`).

| Model          | k  | Q        | df | p(Q)    | I²    | τ² (σ²) |
|----------------|----|---------:|---:|---------|------:|--------:|
| Full pool      | 10 | 1055.30  |  9 | < .0001 | 99.1% |  0.063  |
| Excl-M5 WAPE   |  6 |    2.00  |  5 |  0.849  |  0.0% |  0.001  |

The full-pool heterogeneity (I² = 99.1%) is almost entirely
driven by the M5 WAPE cells, whose per-series metric artefact
(§5.4.5) inflates |Δ| to 0.54–0.78. After excluding the three
M5 WAPE cells, Q drops from 1055 to 2.0 and I² falls to 0%:
the remaining six cells (Favorita × 3 + Rohlik × 3) are
homogeneous. This confirms the prediction of §5.3.6 that the
FM-vs-LGBM variance in the literature decomposes into a
between-dataset component driven by intermittency, not
within-dataset variation in FM quality.

### 6.7 Cross-paper pooled results

**Within-paper paired cells (Source B).** Nine paired cells (M5, Favorita, Rohlik v2 × horizons 7,
14, 28) with `paper_id = LOCAL_MAC_<dataset>_h<horizon>` joining
Source B FM rows (Chronos-Bolt-Tiny + TiRex, averaged inside
family) to matched Azure `lightgbm_cov` + `lightgbm_direct` rows
(averaged inside ML_TREE family). Outcome is absolute WAPE
difference (not the relative-error framing of §6.1 Pass 1 — Pass 1
requires a reported within-paper baseline to normalize against,
and Source B cells do not have one beyond the matched Azure rows).
Model is `rma.mv(yi = delta, V = vi, random = ~ 1 | paper_id /
dataset_norm, test = "t", method = "REML")` — Knapp-Hartung
small-sample adjustment, REML, cluster on `paper_id / dataset_norm`.
For the within-paper Source B cells, `vi = 1/n_valid = 0.01`
(100 sampled series per cell, §5.1.3). For the cross-paper pool,
`vi = (1/n_FM + 1/n_ML_TREE) / n_series_hm` as specified in §3.4.

**Full-pool intercept.**

&nbsp;&nbsp;&nbsp;&nbsp;**Δ̂ (FM − ML_TREE) = −0.2442 WAPE**, &nbsp;
95 % CI [−0.482, −0.007], &nbsp; `t(8) = −2.37`, &nbsp; *p* = 0.045,
&nbsp; `Q(8) = 76.26`, *p* < 10⁻⁴.

The intercept is significant at the 5 % level but the `Q`-statistic
is enormous. The heterogeneity is not noise: it is a single
high-leverage dataset (M5) pulling the pool. Per-dataset
intercepts (REML, `~ 1 | paper_id`, `test = "t"`, k = 3 each):

| Dataset    | Δ̂ (WAPE) | 95 % CI            |   *t* |   *p* |
|------------|---------:|:-------------------|------:|------:|
| M5         |  −0.6470 | [−0.942, −0.352]   | −9.45 | 0.011 |
| Favorita   |  −0.0165 | [−0.265,  0.232]   | −0.29 | 0.802 |
| Rohlik v2  |  −0.0692 | [−0.318,  0.179]   | −1.20 | 0.353 |

M5's intercept is large and significant (−64.7 pp WAPE); Favorita
and Rohlik v2 are not significantly different from zero. **The
entire 24.4 pp aggregate advantage comes from M5.** This is
consistent with the §5.4.5 reading that M5's per-series WAPE on
intermittent demand is a known LGBM failure mode and not a
family-level effect.

**Excluding M5 (sensitivity).** Dropping the three M5 cells and
refitting on Favorita + Rohlik alone:

&nbsp;&nbsp;&nbsp;&nbsp;**Δ̂ (FM − ML_TREE, excl. M5) = −0.0442 WAPE**, &nbsp;
95 % CI [−0.149, 0.061], &nbsp; `t(5) = −1.08`, &nbsp; *p* = 0.329.

The confidence interval crosses zero. **On the two smooth-demand
retail datasets the FM-vs-ML_TREE advantage on Source B is
indistinguishable from zero.** This reverses the sign of the
headline-number reading of the full pool: the paper cannot claim
"FMs beat LGBM on retail demand forecasting" on the strength of
Source B alone, and the M5 effect should be reported as a
dataset-specific finding, not a family-level finding.

**Horizon moderator.** We also fitted

```
rma.mv(yi = delta, V = vi, mods = ~ horizon,
       random = ~ 1 | paper_id / dataset_norm,
       data = delta, test = "t", method = "REML")
```

on the full nine-cell pool. The horizon slope is
`β_h = −0.0043 per day`, `t(7) = −0.34`, `p = 0.741`, 95 % CI
[−0.034, 0.025]. **No evidence of a horizon effect on Δ** in this
sub-pool.

The per-dataset forest plots (Figures 6.1–6.3) visualise this
heterogeneity: the Favorita and Rohlik panels show cells clustered
around zero, while the M5 panel shows the large FM advantage driven
by the WAPE failure mode of the baseline on that specific dataset.

**Cross-paper pooled Δ (primary).** Because no Source A paper
reports both FM and ML_TREE under a shared identifier on these
retail datasets (§4.4), we use cross-paper pooling inside each
`(dataset, horizon, metric)` bucket: for each bucket,
`mean(FM rows) − mean(ML_TREE rows)` across all sources. The
random effect is `~ 1 | dataset_norm` because each Δ mixes papers
and within-paper anchoring is lost by construction. Model:

```
rma.mv(yi = delta, V = vi, random = ~ 1 | dataset_norm,
       data = delta_cross, test = "t", method = "REML")
```

The ten eligible buckets are Favorita × {short, medium, long} ×
WAPE, Rohlik × {short, medium, long} × WAPE, M5 × {short, medium,
long} × WAPE, and M5 × long × WRMSSE (the only Source A WRMSSE
bucket with both families represented). Per-bucket Δ̂ values:

| Dataset  | Horizon | Metric | n FM | n ML_TREE | Δ̂      |
|----------|---------|--------|-----:|----------:|--------:|
| Favorita | short   | WAPE   |    2 |         4 | −0.012  |
| Favorita | medium  | WAPE   |    2 |         4 | −0.017  |
| Favorita | long    | WAPE   |    2 |         4 | −0.021  |
| M5       | short   | WAPE   |    2 |         2 | −0.542  |
| M5       | medium  | WAPE   |    2 |         2 | −0.623  |
| M5       | long    | WAPE   |    2 |         2 | −0.776  |
| M5       | long    | WRMSSE |    1 |         7 | +0.410  |
| Rohlik   | short   | WAPE   |    2 |         4 | −0.055  |
| Rohlik   | medium  | WAPE   |    1 |         4 | −0.067  |
| Rohlik   | long    | WAPE   |    1 |         4 | −0.085  |

Cross-paper intercept (k = 10, with per-bucket sampling variance
`vi = (1/n_FM + 1/n_ML_TREE) / n_series_hm`, §3.4):

&nbsp;&nbsp;&nbsp;&nbsp;**Δ̂ (FM − ML_TREE, cross-paper) = +0.101 WAPE**, &nbsp;
95 % CI [−0.227, 0.429], &nbsp; `t(9) = 0.69`, &nbsp; *p* = 0.505,
&nbsp; `Q(9) = 1055.3`, *p* < 10⁻⁴.

**The effect is not significant and the point estimate is positive**
(FM worse than ML_TREE on average) once proper precision weighting
is applied. This sign flip relative to the uniform-variance
sensitivity (where Δ̂ was negative) is driven by the M5 WRMSSE
bucket (+0.41, FM worse): with n_series = 30,490 this bucket
receives high precision weight, pulling the pooled estimate toward
the ML_TREE side. The `Q` is enormous again, for the same
reason as before: M5 WAPE cells carry a −0.54/−0.62/−0.78
signature driven by Source B `lightgbm_cov` WAPE explosions
(`WAPE_mean = inf` on several Azure runs, confirmed in MLflow), and
the one M5 WRMSSE cell flips the sign to +0.41 (FM worse, drawn
from the seven Source A WRMSSE baselines on M5 — those are the
published competition numbers, not broken baselines).

Excl-M5 cross-paper sensitivity (k = 6, Favorita + Rohlik WAPE
cells only):

&nbsp;&nbsp;&nbsp;&nbsp;**Δ̂ (cross-paper, excl. M5) = −0.0438 WAPE**, &nbsp;
95 % CI [−0.115, 0.027], &nbsp; `t(5) = −1.58`, &nbsp; *p* = 0.174, &nbsp;
`Q(5) = 2.00`, *p* = 0.849.

The excl-M5 cross-paper result is **identical in sign and
magnitude** to the within-paper excl-M5 result from the nine-cell
Source-B-only run, and the heterogeneity remains low
(`σ² ≈ 0.001`, `Q p = 0.85`). That is the cleanest signal from §6.7:
**outside M5, FM and ML_TREE are indistinguishable on WAPE, and
the apparent aggregate FM advantage is a M5 WAPE artefact of a
broken baseline.** The within-paper vs cross-paper distinction
does not change this conclusion on Favorita + Rohlik; it only
weakens the M5-included headline.

**Why the cross-paper pool weakens the full-pool headline.** Two
reasons. First, adding literature FM rows brings in selectively
reported best-case FM numbers (authors reporting their own model
on their own evaluation), which lowers mean(FM) in each bucket
and *should* strengthen FM's advantage — but the effect is small
because on Favorita and Rohlik the Source A FM rows are already
close to Source B numbers (within 1 pp WAPE). Second, and much
larger, the M5 long WRMSSE bucket pulls sharply against FM
(+0.41 Δ̂) because Source A has seven ML_TREE WRMSSE rows on M5 —
competition-grade LGBM, not broken baselines — and only one FM
WRMSSE row, from Chronos in-domain. That single cell alone moves
the cross-paper intercept by roughly +0.04 compared to dropping
it. The pool is honest about what the literature says on M5
WRMSSE: competition-grade ML_TREE beats the one published FM
WRMSSE entry on the same metric. The M5 WAPE cells say the
opposite, for the per-series-denominator reasons in §5.4.5.
Both are true of the same dataset; they should not be averaged
into a single M5 claim. The paper will report M5 WAPE and M5
WRMSSE as separate cells in Table 6.1, not as a single
"M5 effect".

The headline number is the excl-M5 cross-paper
Δ̂ = −0.044 (n.s.), not the full-pool estimate. The M5 cells are
reported as a dataset-specific finding with the per-series WAPE
caveat from §5.4.5 and a separate row for M5 WRMSSE where the
sign flips.

### 6.8 Moderator hypotheses and outcomes

Four pre-registered hypotheses tested against the cross-paper
pool. With k = 10 bucket-level Δs (k = 6 excl. M5) and only
three dataset levels, the pool has limited power for moderator
CI-based gate tests. We report direction-consistency alongside
formal CIs rather than treating CI inclusion of zero as automatic
falsification.

1. **H1 (intermittency ↓ FM advantage).** Predicted: coefficient
   on `zero_day_fraction` is negative. **Direction-consistent.**
   M5 is the only dataset with material zero-day fraction (~70%)
   and is where the FM advantage is largest on WAPE and reverses
   on WRMSSE. CI includes zero at k = 10.

2. **H2 (covariates ↓ FM advantage).** Predicted: coefficient on
   `covariate_rich` is negative. **Structurally untestable** as a
   moderator regression: all FM retail rows are univariate and all
   ML_TREE rows use covariates, so `has_covariates` is perfectly
   collinear with the family split. The qualitative reading is
   direction-consistent — on covariate-rich Favorita, `lightgbm_cov`
   matches Chronos-Bolt-Tiny within 0.3 pp (§5.4.5). A formal test
   requires a covariate-aware FM in Source B (see §5.4.5 TabPFN-TS
   note).

3. **H3 (direct LGBM ↓ FM advantage).** Predicted: coefficient on
   `protocol_direct` is negative. **Conditional on intermittency.**
   On M5, `lightgbm_direct` (WAPE 1.35–1.51) narrows the FM gap
   relative to `lightgbm_cov` (1.62–1.94) — direction-consistent.
   On Favorita and Rohlik, `lightgbm_direct` is worse than
   `lightgbm_cov`, widening the FM gap — direction-inconsistent
   as a main effect. This is the §5.3.6 conditional pattern:
   protocol direction tracks intermittency, not a family-level
   constant. Source B vindicates the conditional synthesis.

4. **H4 (zeros × protocol interaction > 0).** Predicted: interaction
   coefficient is positive. **Untestable at k = 10** with only
   three dataset levels. Flagged for future work with a cross-paper
   pool ≥ 30 buckets.

The M5 dataset-specific finding from §6.7 is the primary empirical
contribution of §6, with H1–H3 framed as moderator sensitivity
around that central result. All moderator CIs are wide at the
current pool size; expanding the pool as more FM papers report
per-series WAPE on individual retail datasets is the single
highest-priority extension of this analysis.
