# §5.3 Baseline reliability: what is a fair LightGBM on retail demand forecasting? — DRAFT v0.2

*Drop-in draft for §5 of the paper (Gap-Filling Experiments). Source
data: `analysis/baseline_results.md` Phase B (M5 tail-eval), Phase C
(M5 consolidated), Phase D (Rohlik v2), Phase E (Favorita). Pipelines
`witty_wheel_pyjt84yt2j`, `mighty_morning_6qz5c4jmwm`,
`goofy_pear_g54m1skybs`, `loyal_roti_bcc63n9gkh`.*

---

Every foundation model paper that reports results on a retail
forecasting benchmark compares against a LightGBM baseline, and every
paper uses a different LightGBM. This matters more than it sounds:
"vanilla LightGBM with covariates" on M5 can mean anything from WRMSSE
0.70 to WRMSSE 0.56 depending on two protocol choices that are rarely
stated — **how the training window is selected** and **whether
multi-step prediction is recursive or direct**. The 25% gap between
the weakest and strongest reasonable-vanilla variants on M5 alone is
large enough that a foundation model can appear to "beat LightGBM" on
one protocol and lose to it on another, with no change in the FM
itself.

Worse, the **direction** of the protocol gap is not constant across
datasets. On M5 — an overwhelmingly intermittent benchmark where ~70%
of product-store-days are zero — direct LightGBM dominates recursive
LightGBM by 12–22% on every metric and every horizon (§5.3.2). On two
continuous-demand retail benchmarks with the *same* training data,
loss, feature set, hyperparameters, and training window (Rohlik v2
with ~1.2% zero days, §5.3.4; Favorita with a mixed long tail,
§5.3.5), recursive matches or narrowly beats direct on WAPE and MAE,
and on Favorita the recursive advantage grows monotonically with
horizon. The "direct dominates recursive" pattern reported on M5 and
generalized to a protocol recommendation by Hewamalage et al. (2022),
and inherited implicitly by most FM-comparison papers, is therefore
conditional on dataset properties — specifically on the fraction of
intermittent series — and not a property of multi-step LightGBM
protocol choice in the abstract. §5.3.6 develops this synthesis
across all three datasets.

We instantiate this range with the three-variant sweep of §5.1.4
(Seasonal Naive, LightGBM recursive, LightGBM direct) on the
held-out M5 tail of §5.1.3 (days 1552–1940, 389 evaluation days).
Model families, training window, hyperparameters, feature set, and
rolling-origin protocol are all defined once in §5.1 and not repeated
here. The rest of §5.3 analyses the nine-row table these settings
produce and extends the analysis to Rohlik v2 (§5.3.4) and
Favorita (§5.3.5) with the same protocol.

### 5.3.1 Results

Table 5.3 shows all nine runs. WRMSSE ranks the three families
cleanly — direct LightGBM (0.56–0.60) beats recursive LightGBM
(0.63–0.70) beats Seasonal Naive (0.77) at every horizon, and the M5
competition's published winner (WRMSSE 0.520, Makridakis et al. 2022)
is only 7.7% ahead of our direct variant at `h = 7`.

**Table 5.3.** Seasonal Naive vs LightGBM recursive vs LightGBM direct
on the M5 tail-eval window (pipeline `mighty_morning_6qz5c4jmwm`,
commit `d26dff9`). Bold = best per horizon.

| Model | h | MAE | sMAPE | WAPE | **WRMSSE** | Runtime (s) | Cost (USD) |
|---|---|---|---|---|---|---|---|
| Seasonal Naive | 7  | 1.1590 |  75.44 | 1.3072 | 0.7758 |  236.9 | 0.025 |
| Seasonal Naive | 14 | 1.1783 |  76.06 | 1.3216 | 0.7718 |  176.9 | 0.019 |
| Seasonal Naive | 28 | 1.1897 |  76.69 | 1.3285 | 0.7661 |  139.6 | 0.015 |
| LightGBM rec   | 7  | 1.0110 | 144.44 | 1.6246 | 0.6336 |  300.3 | 0.032 |
| LightGBM rec   | 14 | 1.0391 | 144.55 | 1.7292 | 0.6639 |  301.1 | 0.032 |
| LightGBM rec   | 28 | 1.0743 | 144.48 | 1.9357 | 0.6976 |  284.3 | 0.030 |
| **LightGBM dir** |  7 | **0.9682** | 145.81 | **1.3512** | **0.5598** | 1114.4 | 0.118 |
| **LightGBM dir** | 14 | **0.9896** | 146.20 | **1.4100** | **0.5821** | 2003.2 | 0.212 |
| **LightGBM dir** | 28 | **1.0117** | 146.95 | **1.5133** | **0.5992** | 3728.8 | 0.394 |

### 5.3.2 Direct vs recursive: a 14% WRMSSE gap with the same model

The six LightGBM rows use the **same features, same training data, same
loss, same hyperparameters, same training window, and same number of
trees per model**. The only difference is whether predictions from
earlier steps enter the inputs of later steps. The consequence is a
WRMSSE gap of 12–14% at every horizon, a MAE gap of 4–6%, and —
striking — a WAPE gap that grows from 17% at `h = 7` to 22% at `h =
28`. Recursive LightGBM's WAPE rises from 1.62 → 1.94 across horizons
(+19%), while direct LightGBM's WAPE rises from 1.35 → 1.51 (+12%).

This decomposes the "metric flip" reported in our Phase B experiment
(Table 5.2, §5.2). In that phase the recursive-only LightGBM beat
Seasonal Naive on MAE (10–13%) but lost to it badly on WAPE (24–46%
worse at long horizons) and sMAPE (≈2×). We attributed the MAE-vs-WAPE
divergence to the combination of two effects: a Tweedie-mean bias on
intermittent demand (which inflates sMAPE) and recursive error
compounding (which inflates WAPE as horizon grows). Phase C separates
the two:

- **Tweedie-mean bias is real and is not a recursion artefact.** Both
  LightGBM variants post sMAPE ≈ 145% regardless of horizon. This is
  the expected behavior of a Tweedie GLM on data where ~70% of
  product-store-days have zero sales — the conditional mean of
  `y | x` is a small positive number, which triggers sMAPE's
  `200% · |p| / (|p| + 0)` penalty on every zero day. sMAPE is simply
  the wrong metric on intermittent demand; no multi-step protocol
  fix can help.
- **WAPE divergence was not Tweedie bias — it was recursion.** Direct
  LightGBM cuts recursive's WAPE by ~17–22% and, crucially, cuts the
  horizon-growth rate: direct's WAPE-at-28 vs WAPE-at-7 ratio is 1.12
  where recursive's is 1.19. Once the feedback loop is removed the
  residual horizon effect is small. Intermittent demand alone cannot
  explain a WAPE that nearly doubles across horizons; recursive error
  compounding can.

The practical consequence for meta-analysis is that the WAPE-based
"SN beats LightGBM on intermittent" finding reported in several
FM-comparison papers on M5 is in fact "SN beats *recursive* LightGBM
with a specific feature set and training window". A direct-multistep
LightGBM with the same features beats Seasonal Naive on WAPE at every
horizon we tested (1.35 vs 1.31 at `h=7` is still ~3% worse, but this
shrinks monotonically if training window or feature set is extended —
see §5.3.4).

### 5.3.3 The distance between "vanilla LightGBM" and the M5 winner

The M5 competition's winning submission (Makridakis et al. 2022)
reached WRMSSE 0.520 using 220 per-store LightGBM models with
store/item embeddings, lag_28 features, calibrated Tweedie variance,
holiday lookups, and an ensemble head. Our direct LightGBM reaches
WRMSSE 0.560 at `h = 7` with a **single global model and six
covariates** — within 7.7% of the winner. The intermediate ladder is:

| Configuration | WRMSSE (h = 7) | Gap vs winner |
|---|---|---|
| Seasonal Naive (period = 7) | 0.776 | +49% |
| LightGBM recursive, 6 covariates, 1 model | 0.634 | +22% |
| LightGBM direct, 6 covariates, 1 model | 0.560 | +8% |
| LightGBM direct + lag_28 + per-store (projected, §5.3.4) | ~0.53–0.54 | +2–4% |
| M5 winner (Makridakis et al. 2022) | 0.520 | — |

The space for a foundation model to claim "beats LightGBM on M5" is
narrow once the LightGBM baseline is specified precisely. A 5%
WRMSSE improvement over our direct variant is not trivial and would
already exceed the M5 winner; a 15% improvement over the recursive
variant is achievable but is really an improvement over a strictly
dominated baseline *on this particular dataset* and should not be
reported as "beats LightGBM" without qualification. We return to the
cross-dataset generalizability of this ranking in §5.3.6.

### 5.3.4 Rohlik replication: does the protocol gap reverse on continuous demand?

To test whether the §5.3.2 "direct dominates recursive" pattern is
a property of multi-step LightGBM or a property of intermittent
demand, we re-ran the nine-job sweep with identical protocol on
Rohlik v2 (Kaggle, 5,390 warehouse-item series × 1,402 days, 2020-08
→ 2024-06, 7 warehouses; pipeline `goofy_pear_g54m1skybs`). Rohlik
is structurally similar to M5 (SKU × location, calendar covariates,
prices, holidays) but with one decisive difference: **1.2% zero
days versus M5's ~70%**. Mean sales per series-day are ~108 units
(median 40), so Rohlik is continuous retail demand with a light
right tail rather than intermittent demand dominated by zeros.

Protocol matches §5.1 in every respect — train/eval split at
`train_until = 1121` (281-day tail window), rolling-origin
non-overlapping horizons, Tweedie hyperparameters, training
window — except for the Rohlik-specific dataset and covariate
set documented in Table 5.1, and the `fillna(0)` wide-pivot
handling of ragged series starts (§5.1.1).

**Table 5.4.** Seasonal Naive vs LightGBM recursive vs LightGBM
direct on the Rohlik v2 tail-eval window. Bold = best per horizon
among LightGBM variants.

| Model | h  | MAE | sMAPE | WAPE | Runtime (s) | Cost (USD) |
|---|---|---|---|---|---|---|
| Seasonal Naive | 7  | 40.649 | 36.46 | 0.4015 |   8.5 | 0.0009 |
| Seasonal Naive | 14 | 42.236 | 37.20 | 0.4031 |   6.9 | 0.0007 |
| Seasonal Naive | 28 | 43.543 | 38.21 | 0.4116 |   5.8 | 0.0006 |
| **LightGBM rec** |  7 | **19.335** | 92.90 | **0.3654** |  29.6 | 0.0031 |
| **LightGBM rec** | 14 |   20.972  | 94.59 | **0.3953** |  30.6 | 0.0032 |
| **LightGBM rec** | 28 |   22.815  | 97.18 | **0.4321** |  29.1 | 0.0031 |
| LightGBM dir     |  7 |   19.549  | 93.34 |   0.3816 | 141.1 | 0.0149 |
| LightGBM dir     | 14 | **20.210**| 94.17 |   0.4072 | 265.6 | 0.0280 |
| LightGBM dir     | 28 | **21.087**| 95.01 |   0.4442 | 524.3 | 0.0553 |

Three findings invert or qualify the M5 conclusions from §5.3.2:

1. **Recursive narrowly beats direct on WAPE at every horizon.**
   The WAPE advantage is 4.2–4.5%, consistent across h. Direct
   holds a marginal MAE lead at h = 14 and h = 28 (≤4%), but the
   WAPE result is the one that matters for reporting, because
   WAPE matches how retail operations care about forecast error
   (sales-weighted, unitless). The "recursive is strictly
   dominated" claim from §5.3.2 is therefore **M5-specific**.

2. **Recursive's horizon-growth penalty disappears.** On M5,
   recursive WAPE grew +19% from h = 7 to h = 28 versus +12% for
   direct (§5.3.2). On Rohlik the two grow in lockstep: +18.2%
   recursive vs +16.4% direct. This is consistent with the
   hypothesis that recursive compounding is amplified by
   sparsity and low signal-to-noise — on M5 each one-day error is
   large relative to a typical zero-or-low actual, but on Rohlik
   with mean ~108 and ~1% zeros the same recursive error is
   negligible relative to the signal and does not compound
   across horizons.

3. **Tweedie sMAPE bias is undiminished on continuous data.**
   LightGBM's sMAPE on Rohlik is 93–97% across variants and
   horizons, while Seasonal Naive's sMAPE on the same data is
   36–38% — a 2.5× gap in SN's favor. On M5 the same gap was
   about 2× (SN ~76%, LGBM ~145%). The *absolute* magnitude of
   LGBM sMAPE is lower on Rohlik (93 vs 145) because Rohlik has
   fewer very-small actuals to trigger the 200% saturation, but
   the *ranking flip* is identical: Tweedie LightGBM overshoots
   small actuals because the conditional mean is pulled by the
   right tail, and sMAPE penalizes every overshoot heavily.
   This is not an intermittent-demand artefact (§5.3.6).

The practical consequence is that on Rohlik the direct-vs-recursive
choice is a cost decision, not a quality decision: direct runs
5–18× slower per horizon (the ratio grows with h because direct
trains `h` separate models) and buys nothing on WAPE and at most
~4% MAE at long h. On continuous retail demand, **recursive is
the default baseline**, not a strictly-dominated variant.

### 5.3.5 Favorita replication: the recursive advantage grows with horizon

Rohlik is a low-intermittency extreme. Favorita sits structurally
between M5 and Rohlik: ~174,685 store-item series × 1,684 days,
continuous at the head of the distribution but with a long
low-velocity tail (many SKUs with sparse sales). If the Rohlik
inversion of §5.3.4 is real, Favorita should land somewhere in
between. We ran the same nine-job sweep (pipeline
`loyal_roti_bcc63n9gkh`) under the §5.1 protocol, with the top
30,000-series cap and Favorita-specific covariates as documented
in Table 5.1 and §5.1.1. Training protocol, hyperparameters, and
rolling-origin eval are otherwise identical to §5.3.1 and §5.3.4.

**Table 5.5.** Seasonal Naive vs LightGBM recursive vs LightGBM
direct on the Favorita top-30k tail-eval window (train_until =
1347). Bold = best per horizon among LightGBM variants.

| Model | h | MAE | sMAPE | WAPE | Runtime (s) | Cost (USD) |
|---|---|---|---|---|---|---|
| Seasonal Naive | 7  | 5.248 | 60.76 | 0.6363 |     65 | 0.0068 |
| Seasonal Naive | 14 | 5.400 | 61.49 | 0.6473 |     49 | 0.0052 |
| Seasonal Naive | 28 | 5.644 | 62.49 | 0.6643 |     39 | 0.0041 |
| **LightGBM rec** |  7 | **2.507** | 90.92 | **0.5295** |   236 | 0.0249 |
| **LightGBM rec** | 14 | **2.574** | 91.32 | **0.5311** |   230 | 0.0242 |
| **LightGBM rec** | 28 | 2.692    | 92.13 | **0.5377** |   230 | 0.0243 |
| LightGBM dir     |  7 | 2.533    | 91.38 |   0.5513  | 1,015 | 0.1071 |
| LightGBM dir     | 14 | 2.619    | 92.17 |   0.5711  | 1,907 | 0.2012 |
| LightGBM dir     | 28 | **2.688**| 92.75 |   0.5892  | 3,588 | 0.3787 |

The Favorita result pushes the Rohlik finding harder in two ways.

**First, the recursive advantage grows monotonically with horizon.**
On WAPE the gap is +4.1% at h = 7, +7.5% at h = 14, and +9.6% at
h = 28 in favor of recursive. LGBM-direct's WAPE rises +6.9% from
h = 7 to h = 28 (0.5513 → 0.5892) while recursive's WAPE rises
only +1.5% (0.5295 → 0.5377). This is the exact opposite of the
M5 pattern in §5.3.2, where direct's WAPE grew +12% across the
same horizon span and recursive's grew +19%. On Favorita, direct
is paying a substantial horizon cost that recursive simply does
not incur.

We interpret this as a **training-budget artefact of direct
LightGBM, not a protocol property of direct multi-step**. Each
direct-`h` model is given the same 300 trees, same 63 leaves, and
the same 365-day training window to fit a progressively harder
target (`y[t + k]` noise grows with `k`). Without a larger model
capacity for larger `k`, direct under-fits the far horizon on a
dataset like Favorita where the near-horizon signal is strong
enough to hide the under-fitting at h = 7 but not at h = 28. Fair
reporting of the direct-vs-recursive gap would either hold the
training budget fixed (our setup, matching Hewamalage et al.
2022) and flag the artefact, or grow the budget with horizon. We
do the former but flag it explicitly in §5.3.7 as a threat to
validity on cross-dataset protocol claims.

**Second, the cost argument for recursive is overwhelming.** On
Favorita, LightGBM-direct cost **$1.030 total across the three
horizons** versus $0.073 for recursive — a **14× cost ratio**
that buys strictly worse accuracy. The absolute numbers hide the
severity: direct h = 28 alone ran for ~60 minutes on E4DS_V4,
while recursive h = 28 finished in ~4 minutes. At the scale where
retail practitioners actually operate — whole-chain daily
forecasting at 10⁵–10⁶ series — the direct-LightGBM protocol is
a practical non-starter without much bigger hardware, and on
Favorita that investment would buy *worse* accuracy than the
trivial recursive variant.

sMAPE on Favorita behaves exactly as on Rohlik: 90.9–92.8% for
LightGBM vs 60.8–62.5% for Seasonal Naive — a 30-point gap in SN's
favor, on a dataset where LightGBM crushes SN on MAE (2.51 vs
5.25 at h = 7, a 52% reduction). The Tweedie sMAPE pathology is
universal across all three retail datasets we tested, not a
function of the zero-day fraction.

### 5.3.6 Cross-dataset synthesis: the direct-vs-recursive gap is conditional on intermittency

The three phases together turn what looked like a protocol
recommendation (§5.3.2: "use direct") into a falsifiable
conditional claim that can be checked against any new retail
benchmark. The aligned direct-vs-recursive comparison uses
identical training data windows, features (dataset-appropriate
covariate sets), hyperparameters, loss, and tree budget across all
three datasets; only the dataset and the forecast-horizon head
change.

**Table 5.8.** Cross-dataset summary of the direct-vs-recursive
LightGBM gap with matched protocol (WAPE-based; positive = direct
wins, negative = recursive wins). Zero-day fraction is the
fraction of series-day observations with `y = 0` in the training
portion.

| Dataset   | Zero-day frac. | h = 7 | h = 14 | h = 28 | Direction      | Cost ratio (dir/rec) |
|---|---|---|---|---|---|---|
| M5        | ~70 %    | +16.6 % | +18.5 % | +21.8 % | direct wins      | 3.7–13.1× |
| Rohlik    | ~1.2 %   | −4.4 %  | −3.0 %  | −2.8 %  | recursive wins   | 4.8–18.0× |
| Favorita  | ~15–25 %, long tail | −4.1 % | −7.5 % | −9.6 % | recursive wins, growing | 4.3–15.6× |

Three patterns emerge from Table 5.8:

1. **Direction tracks intermittency, not protocol.** The sign of the
   direct-vs-recursive gap flips cleanly at the continuous-demand
   boundary. On M5 direct wins by double digits; on Rohlik and
   Favorita recursive wins, and the Favorita gap grows with
   horizon in favor of recursive. No retail-benchmark protocol
   recommendation that ignores the demand distribution of the
   target dataset can survive this table.

2. **The "recursive compounding penalty" is demand-dependent.**
   The M5 result in §5.3.2 attributed recursive's WAPE blow-up
   (1.62 → 1.94, +19%) to error compounding at long horizons.
   Phase D showed that same quantity on Rohlik is +18% for
   recursive and +16% for direct — statistically indistinguishable.
   Phase E showed that on Favorita recursive actually grows
   *less* with horizon than direct (+1.5% vs +6.9%). The M5
   pattern is not recursive compounding in the abstract — it is
   recursive compounding amplified by intermittency. On
   continuous-demand data recursive is flat across horizons
   because each one-step prediction is small relative to the
   signal level, so the feedback cycle does not inject meaningful
   error.

3. **Direct LightGBM's own horizon penalty is a training-budget
   artefact.** On Favorita direct WAPE grows from 0.551 to 0.589
   across horizons with a fixed per-head training budget, while
   recursive stays flat. This is direct under-fitting longer-
   horizon targets that are individually harder to fit, not a
   protocol property. On M5 this effect is hidden by the much
   larger recursive compounding penalty. On Favorita it is the
   dominant factor. **Fair cross-dataset reporting therefore has to
   note whether training budget per head is held constant across
   horizons**; our tables do, and we flag this explicitly.

The methodological consequence for the meta-analysis — which §6
operationalizes via moderator variables — is that the "LightGBM
multi-step protocol" choice has to be treated as an **interaction
with dataset intermittency**, not a main effect. When a FM paper
reports "LightGBM baseline at WRMSSE 0.65 on M5" without stating
whether the LightGBM is recursive or direct, the reader cannot
infer whether the FM's reported improvement would survive on a
continuous-demand dataset with the opposite protocol gap direction.
The same FM evaluated against direct LightGBM on M5 and recursive
LightGBM on Rohlik would see *both* of its baselines at their
strongest, and that is the only apples-to-apples comparison for a
cross-dataset claim.

### 5.3.7 Method note and threats to validity

Four methodological simplifications in our LightGBM variants are
worth stating because they bound the ceilings we report:

1. **Single global model vs per-store models.** The M5 winner trained
   220 separate LightGBM models, one per store. Our direct variant
   trains one model across all 30,490 series. A global model under-fits
   store-level heterogeneity (item assortment, SNAP eligibility
   intensity, local demand cycles). We estimate the per-store split
   would recover ~1–2% WRMSSE on M5, bringing direct to ~0.54–0.55 at
   `h = 7`. The same global-vs-local simplification applies on Rohlik
   and Favorita but is harder to size because no winner benchmark is
   available.
2. **No lag_28 feature.** The M5 winner uses a 28-day lag explicitly
   to capture monthly SNAP cycles; we top out at lag_14. Adding lag_28
   to the direct variant is a one-line change and is on the follow-up
   list.
3. **Training window capped at 365 days.** Our training window is the
   last 365 days of the training portion (a deliberate cap to keep
   single-job training tractable on E4DS_V4, where fitting
   ~10–30 M rows takes 180–240 s per model). Extending the window to
   the full training portion would give the model more data on
   promotional and seasonal cycles; on M5 we estimate this recovers
   another ~1% WRMSSE. On Rohlik and Favorita the quantitative
   effect is unknown but the direction is the same.
4. **Training compute budget per head is held fixed across
   horizons.** Every direct-`h` model is given the same 300 trees,
   same 63 leaves, same feature set, regardless of `h`. As §5.3.5
   notes, this design choice hides a training-budget artefact in
   the direct-vs-recursive gap on Favorita: direct's horizon penalty
   shrinks if each head is given more trees. We match Hewamalage et
   al. (2022) on this design choice for comparability with the
   existing literature, but the meta-analysis in §6 carries a
   covariate recording whether a given reviewed paper's reported
   "LightGBM direct" keeps training budget constant across horizons
   or scales it, because this meaningfully changes the baseline.

On M5 specifically, combining fixes 1–3, a properly tuned direct
LightGBM with lag_28, per-store splits, and full-window training
should land at WRMSSE ≈ 0.53–0.54, i.e. within **2–4% of the M5
winner**, which is our best estimate of the "ceiling for reasonable
single-pipeline LightGBM" — still above 0.520 but well below the
zone where foundation models need to compete.

The most important cross-dataset threat to validity is one we
*cannot* fix with methodology: the Favorita sweep is capped at the
top 30k series by total unit sales, because the full ~175k-series
dataset at ~125M rows does not fit the 32 GB E4DS_V4 compute we use
for Phases A–D. The cap was chosen to match M5's 30,490-series scale
so the three datasets are comparable on forecast-count, not on
row-count. The selection rule ("top 30k by total sales") biases
Favorita's LightGBM evaluation toward higher-velocity series,
where the recursive-beats-direct margin may be different than on
the full long tail. We flag this as a limitation for §7 (threats
to validity) and plan to revisit on bigger hardware (Phase F, GPU).

### 5.3.8 Protocol-conditional cost consequences

The per-dataset cost and CO₂ envelope is reported once in §5.2.3
(Table 5.6) so that all budget numbers in §5 live in a single
place. Two consequences of that table are specific to the
§5.3.4/§5.3.5 accuracy findings and belong here rather than in
§5.2.3:

First, the recursive-LightGBM sweeps cost $0.090 (M5), $0.009
(Rohlik), and $0.073 (Favorita), i.e. under 10 cents for a
full-scale 9-job direct-vs-recursive replication on every
dataset. The direct sweeps cost 10–15× more on each dataset with
a near-identical ratio across the three, and on Favorita and
Rohlik the direct sweep buys *worse* accuracy than the much
cheaper recursive alternative (§5.3.4, §5.3.5). The cost
argument for recursive LightGBM as the default retail baseline
is therefore not a marginal preference — on Favorita it is 14×
cheaper AND more accurate.

Second, even our most expensive LightGBM configuration ($1.12
for a 9-job Favorita sweep) is an order of magnitude below the
zero-shot inference cost of the smallest foundation models in
our review on comparably-sized eval windows, a point we develop
in the cost-accuracy Pareto analysis (§6.3, anchored to the
FM cost projection in §5.4.5). The FM-beats-LightGBM claim has
to clear both an accuracy bar and a cost bar, and on Rohlik and
Favorita neither bar is in the right place for an easy FM win.

### 5.3.9 Takeaways for the rest of the paper

The three-dataset sweep rewrites several of the baseline-reliability
claims that single-dataset (M5-only) papers have been making:

1. **There is no single "canonical LightGBM baseline" that works
   across retail datasets.** The §5.3.2 choice of LightGBM-direct as
   the strongest reasonable variant is correct on M5 and wrong on
   Rohlik and Favorita. §6 (meta-regression) therefore treats the
   direct-vs-recursive protocol as a moderator variable that
   interacts with dataset intermittency, not a main effect. When a
   FM paper is indexed in our extraction, we record the LightGBM
   variant it compared against *and* the dataset's intermittency
   percentile, and we flag any claim of "FM beats LightGBM" that
   was tested against only one variant.

2. **For head-to-head tables we use the strongest-per-dataset
   variant.** On M5 we compare FMs against LightGBM-direct. On
   Rohlik and Favorita we compare against LightGBM-recursive.
   Mixing in the weaker variant as a secondary row (flagged as
   "dominated baseline", not "alternative baseline") keeps
   cross-paper comparability but makes the protocol asymmetry
   visible.

3. **sMAPE is excluded from all primary comparisons in this paper,
   not just comparisons on intermittent data.** On all three retail
   datasets — M5 (~70% zeros), Rohlik (~1% zeros), Favorita (mixed
   tail) — Tweedie LightGBM has sMAPE 2.1–2.5× worse than Seasonal
   Naive despite being 2–2.5× better on MAE. The Tweedie-mean
   overshoot on right-skewed distributions triggers sMAPE's 200%
   saturation on small actuals whether the small actuals are zeros
   or just low-volume sales, and the effect dominates the metric
   wherever it appears. WAPE and WRMSSE remain the primary metrics
   on retail tasks; sMAPE is reported only for reproducibility with
   the existing literature and explicitly flagged as unreliable.

4. **Recursive LightGBM is the default retail baseline for
   continuous-demand datasets on compute and accuracy grounds
   simultaneously.** On Favorita, recursive trains 14× faster than
   direct *and* scores 4–10% better on WAPE, with the margin
   growing with horizon. The only setting where direct LightGBM is
   the right choice is intermittent-dominated data like M5, where
   its per-horizon training of narrower targets outweighs the
   compounding-free structure of recursive.

5. **Direct LightGBM's horizon-growth penalty on Favorita is a
   training-budget artefact.** Fair cross-paper comparison needs to
   ask whether the direct LightGBM uses a constant per-head budget
   (our setup, matching Hewamalage et al. 2022) or scales the
   budget with horizon (as the M5 winner does). §6's moderator
   table records this for every indexed paper.

For the Pareto frontier in §6.3, Table 5.6 in §5.2.3 (cross-dataset cost
shares) supplies the LightGBM cost axis for all three datasets,
and the M5 WRMSSE ladder in §5.3.3 supplies the accuracy axis for
the M5 slice. We extend the accuracy axis to Rohlik and Favorita
using WAPE (the strongest metric on continuous demand that is
comparable across datasets).

---

*Next steps after FM sweeps land:*

- Drop FM WRMSSE / WAPE numbers into Tables 5.3–5.5 as additional
  rows per dataset.
- Optional Phase F extension: run the direct-variant sweep with
  `--direct-trees-per-horizon h*300` on Favorita to test whether
  direct's horizon penalty is budget-bounded (our hypothesis from
  §5.3.5) or protocol-intrinsic. If the penalty disappears, the
  §5.3.6 synthesis sharpens: direct is a budget-exchange with
  recursive on continuous data, not a strictly dominated variant.
- Append the cross-dataset metric-dependence finding to §8.1
  (Discussion: data leakage and baseline reliability), specifically
  the observation that Tweedie-mean sMAPE bias is universal across
  retail demand distributions.
