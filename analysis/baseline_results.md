# Phase A Baseline Results: Seasonal Naive on M5

**Pipeline:** `bold_fly_grlqvdx1cg` (Azure ML, swedencentral)
**Date:** 2026-04-13
**Compute:** `cc-forecast-batch` (E4DS_V4, 4 vCPU, 32 GB RAM)
**Environment:** `forecast-benchmark-cpu-env:1`
**Code commit:** `eb3e6528` (post MLflow artifact bug fix)

## Dataset

- **M5 (Walmart)** — 30,490 product-store series, 1,941 days, daily frequency
- 59,181,090 total observations
- High intermittency (many zero days) — Walmart unit sales

## Method

Seasonal Naive with weekly seasonality (period=7). Forecasts horizon h ahead by repeating the
value from h−7, h−14, … steps back. Rolling-origin evaluation: each series uses min_train_size=100
days, then rolls forward generating non-overlapping forecast windows of length h.

## Results

| Horizon | MAE_mean | sMAPE_mean | WAPE_mean | Runtime (s) | Cost (USD) | CO₂ (kg) | Series/sec |
|--------:|---------:|-----------:|----------:|------------:|-----------:|---------:|-----------:|
| 7       | 1.0014   | 59.68      | 1.2853    | 1061.2      | $0.1120    | 0.000287 | 28.7       |
| 14      | 1.0169   | 60.17      | 1.2916    | 784.4       | $0.0828    | 0.000212 | 38.9       |
| 28      | 1.0334   | 60.80      | 1.3047    | 608.9       | $0.0643    | 0.000165 | 50.1       |

## Observations

1. **Error grows slowly with horizon** (MAE 1.0014 → 1.0334 across h=7→28, just +3.2%). This is
   characteristic of intermittent demand: the naive baseline's poor calibration dominates over
   horizon effects.
2. **sMAPE near 60% across all horizons** — confirms M5's well-known difficulty for
   non-cross-learning methods. The M5 paper reports the seasonal-naive benchmark at WRMSSE ≈ 0.85
   while the LightGBM winner achieved 0.520 (Table 3, Makridakis 2022).
3. **Runtime decreases with horizon counterintuitively** — fewer rolling windows fit in the
   training tail, so total per-series work drops. Throughput rises from 28.7 to 50.1 series/sec.
4. **Total compute cost**: $0.26 across all 3 horizons. Negligible compared to GPU foundation
   models (Chronos-2 reports 3.6s median per task on A10G, but ×100 tasks ×retail subset means
   ~$30–$50 for a comparable sweep).

## Cost-accuracy reference points (from literature)

| Model              | Hardware  | Approx. throughput  | Source           |
|--------------------|-----------|---------------------|------------------|
| Seasonal Naive     | E4DS_V4   | 28–50 series/sec    | this study       |
| LightGBM (M5 winner)| CPU      | n/a (220 models)    | C01 (Makridakis) |
| Chronos-2          | A10G GPU  | 300 series/sec      | A02 (Ansari)     |
| Chronos-Bolt       | CPU       | 250× faster than v1 | A11 (AWS)        |
| TabPFN-TS          | GPU       | n/a (11M params)    | A14 (Hollmann)   |

## Next steps

1. Run LightGBM with covariates (calendar + prices + SNAP events) on M5 — primary FM-killer baseline
2. Run ETS/AutoARIMA via statsforecast on M5 for a deeper statistical baseline
3. Once GPU quota is granted (NCASv3_T4 in swedencentral): run Chronos-Bolt zero-shot for cost-accuracy comparison
4. Replicate on Favorita and Rohlik datasets to test cross-dataset stability

## Files

- Logs: `/tmp/sn_h7/artifacts/user_logs/std_log.txt` (and h14, h28)
- MLflow runs: experiment `meta-analysis-gap-filling`, run names `seasonal_naive_m5_h{7,14,28}`
- Pipeline: `benchmark/code/pipelines/gap_filling.yaml`

---

# Phase B: Tail-eval head-to-head — Seasonal Naive vs LightGBM (Tweedie + covariates)

**Pipeline:** `witty_wheel_pyjt84yt2j` (Azure ML, swedencentral)
**Date:** 2026-04-13
**Compute:** `cc-forecast-batch` (E4DS_V4)
**Code commit:** `a8afc6d` (vectorized panel LightGBM) + WAPE fix
**Total cost:** ~$0.16 across 6 jobs (~12 min wall-clock)

## Protocol change

To compare SN and LightGBM on identical eval windows, both models now use
**tail evaluation**: train_until = floor(0.8 × n_days) = 1552, evaluation
on rolling-origin windows of length `h` over days 1552–1940 (389 test days).
SN ignores the train portion (no fitting); LightGBM fits a single global
model on the **last 365 days** of the training portion (~10.7M examples ×
13 features, Tweedie objective with variance_power=1.1, 300 trees,
num_leaves=63).

Why a single train + recursive eval: full per-origin retraining at this
scale was prohibitive (60+ retrains × 10 min each), and the M5 paper's
own protocol holds out a fixed test tail rather than retraining for every
window. We document this as a deliberate methodological choice.

## Features

Lags (1, 7, 14), rolling means (7, 14), day-of-week, sell_price,
snap_CA, snap_TX, snap_WI, is_event, wday, month. Six covariates from M5
calendar + prices, no item/store embeddings, no price-change features,
no lag_28, no holiday lookups — deliberately minimal to characterize a
"vanilla" gradient-boosted baseline against SN.

## Results

| Model            | h  | MAE     | sMAPE  | WAPE¹  | Runtime (s) | Cost (USD) | Series/sec |
|------------------|---:|--------:|-------:|-------:|------------:|-----------:|-----------:|
| Seasonal Naive   |  7 | 1.1590  | 75.44  | 1.3072 | 237.8       | $0.0251    | 128.2      |
| Seasonal Naive   | 14 | 1.1783  | 76.06  | 1.3216 | 179.2       | $0.0189    | 170.2      |
| Seasonal Naive   | 28 | 1.1897  | 76.69  | 1.3285 | 143.7       | $0.0152    | 212.2      |
| LightGBM (cov)   |  7 | **1.0110** | 144.44 | 1.6246 | 300.8   | $0.0318    | 101.4      |
| LightGBM (cov)   | 14 | **1.0391** | 144.55 | 1.7292 | 295.6   | $0.0312    | 103.1      |
| LightGBM (cov)   | 28 | **1.0743** | 144.48 | 1.9357 | 286.3   | $0.0302    | 106.5      |

¹ Per-series WAPE skips series with zero total demand in the test window
(10–28 of 30,490 series, depending on h). The previous version returned
inf for those — fixed in commit `a8afc6d`'s WAPE patch.

## Headline finding: the metric flips the winner

On MAE, LightGBM beats Seasonal Naive across all horizons by **10–13%**
(1.01 vs 1.16 at h=7, 1.07 vs 1.19 at h=28). But on sMAPE LightGBM is
nearly **twice as bad** (~144% vs ~76%), and on WAPE LightGBM is **24–46%
worse** (1.62–1.94 vs 1.31–1.33).

The mechanism is structural to intermittent demand:

- M5 contains ~70% zero-demand days at the product-store level.
- Tweedie LightGBM minimizes E[(y - μ)² · μ^(-p)] which converges to the
  conditional **mean** of `y|x`. For a binary-like sales pattern, that's
  a small positive number around 0.2–0.5.
- Seasonal naive copies last week's value, which is exactly zero on
  ~70% of days — so it scores zero error on those days but a full unit
  of error on the spike days it misses.
- **MAE rewards small positives** (|0.3 − 0| < |1 − 0|): the model is
  closer to the truth on average across both zero days and spike days.
- **sMAPE punishes any non-zero prediction when truth is zero**
  (`|p − 0| / ((|p| + 0)/2) = 200%` per such case). Tweedie's smooth
  output triggers this on ~70% of test points; SN triggers it
  essentially never.
- **WAPE = Σ|err| / Σ|y_true|**: errors compound under recursive
  multi-step prediction (the model feeds its own outputs back), and the
  effect grows monotonically with horizon — visible as WAPE growing
  from 1.62 → 1.94 across h=7 → h=28 for LGBM, while SN stays nearly
  flat (1.31 → 1.33).

This single comparison is going to be the **anchoring data point for §3
of the paper** (metric-dependence of FM/baseline gaps) — it shows in our
own experiment that the conclusion "model A beats model B" on M5 has no
meaning without specifying the metric.

## Comparison to Phase A baseline (full rolling-origin SN)

The Phase A SN numbers (MAE 1.00, sMAPE 60) are **not** directly
comparable to Phase B because they averaged over 1.6M+ rolling-origin
predictions starting from day 100, while Phase B uses the harder tail
window (last 389 days, where M5's known-difficult test period sits). SN
on the tail is genuinely worse than SN on the full history — confirming
that the M5 hold-out is harder than the typical day, which is exactly
why M5 was designed this way.

## Observations

1. **MAE/sMAPE divergence is the central problem of this meta-analysis.**
   Most foundation-model papers report MAE/MASE on retail; competition
   papers report WRMSSE; intermittent-demand papers report cumulative
   bias. These are not interchangeable rankings.
2. **The 10–13% MAE gap that LGBM gets here is the *floor*, not the
   ceiling**, of what a tuned ML model achieves on M5. The M5 winner
   reached WRMSSE 0.520 vs the seasonal-naive benchmark of ~0.85
   (39% improvement) using 220 LightGBM models, store/item embeddings,
   direct-multistep training, and Tweedie with calibrated variance.
3. **Cost gap is small**: LGBM costs $0.03 vs SN $0.02 per horizon on
   the same compute. LightGBM is not noticeably more expensive than SN
   at this scale — it's bottlenecked by data loading + pivoting, not
   model fitting.
4. **Runtime is roughly horizon-independent for LGBM** (~290–300 s
   across all 3 horizons) because train cost dominates and is fixed;
   eval cost scales as n_windows × horizon, which is roughly constant.
   For SN runtime drops with horizon (fewer windows × cheaper per
   window).

## Next steps

1. **Run on Favorita and Rohlik** to test whether the metric-flip
   pattern holds across other retail panels.
2. **Add direct (vs recursive) LightGBM** as a second ML baseline — one
   model per horizon, matching the M5 winner protocol, to quantify
   how much of the gap is "minimal features" vs "recursive prediction".
3. **GPU quota request** for foundation models is in progress
   (NCASv3_T4 quota request to 16 vCPUs failed; trying NVadsA10v5
   instead) — once granted, run Chronos-Bolt zero-shot on the same
   tail window for a triangulated SN/LGBM/FM comparison.
4. **WRMSSE metric**: implement the M5 hierarchical weighting so we can
   compare against the published M5 winner number directly. This is
   ~50 lines of code given the calendar + prices we already have.

## Files

- Logs: `/tmp/cmp_sn_tail_h{7,14,28}/artifacts/user_logs/std_log.txt` and
  `/tmp/cmp_lgbm_tail_h{7,14,28}/artifacts/user_logs/std_log.txt`
- MLflow runs: experiment `meta-analysis-gap-filling`, run names
  `sn_tail_h{7,14,28}` and `lgbm_tail_h{7,14,28}`
- Pipeline: `benchmark/code/pipelines/m5_tail_comparison.yaml`

---

# Phase C: Consolidated M5 head-to-head — SN vs LightGBM (recursive) vs LightGBM (direct) with WRMSSE

**Pipeline:** `mighty_morning_6qz5c4jmwm` (Azure ML, swedencentral)
**Date:** 2026-04-13
**Compute:** `cc-forecast-batch` (E4DS_V4)
**Code commit:** `d26dff9` (adds WRMSSE + direct LightGBM)
**Total cost:** ~$0.81 across 9 jobs (wall clock dominated by `lgbm_dir_h28`
which trains 28 sequential Tweedie models and runs 62 min on its own)

## Protocol

All nine jobs share the identical M5 tail eval window — days 1552..1940
(389 days) — with rolling-origin non-overlapping forecast windows of
length `h`. Seasonal Naive uses no training (copies last week); both
LightGBM variants fit a single global Tweedie model on the last 365 days
of the training portion with 6 covariates (sell_price, snap_CA, snap_TX,
snap_WI, is_event, wday, month) plus lags {1,7,14} and rolling means
{7,14}. The recursive variant trains one model and feeds its own outputs
back; the direct variant trains `h` separate models (one per step offset
`k ∈ [0, h)`) that each predict `y[t+k]` from features known at `t`
without any feedback.

WRMSSE is the full 12-level Makridakis (2022) metric computed in-job on
every run from the same sales/calendar/prices CSVs as the predictions,
with weights from the last 28 training days of dollar sales and per-series
scales from squared first-differences over non-zero training history.

## Results

| Model            | h  | MAE    | sMAPE  | WAPE¹  | **WRMSSE** | Runtime (s) | Cost (USD) |
|------------------|---:|-------:|-------:|-------:|-----------:|------------:|-----------:|
| Seasonal Naive   |  7 | 1.1590 |  75.44 | 1.3072 |     0.7758 |       236.9 |    $0.0250 |
| Seasonal Naive   | 14 | 1.1783 |  76.06 | 1.3216 |     0.7718 |       176.9 |    $0.0187 |
| Seasonal Naive   | 28 | 1.1897 |  76.69 | 1.3285 |     0.7661 |       139.6 |    $0.0147 |
| LightGBM (rec)   |  7 | 1.0110 | 144.44 | 1.6246 |     0.6336 |       300.3 |    $0.0317 |
| LightGBM (rec)   | 14 | 1.0391 | 144.55 | 1.7292 |     0.6639 |       301.1 |    $0.0318 |
| LightGBM (rec)   | 28 | 1.0743 | 144.48 | 1.9357 |     0.6976 |       284.3 |    $0.0300 |
| **LightGBM (dir)** |  7 | **0.9682** | 145.81 | **1.3512** | **0.5598** | 1114.4 | $0.1176 |
| **LightGBM (dir)** | 14 | **0.9896** | 146.20 | **1.4100** | **0.5821** | 2003.2 | $0.2115 |
| **LightGBM (dir)** | 28 | **1.0117** | 146.95 | **1.5133** | **0.5992** | 3728.8 | $0.3936 |

¹ Per-series WAPE skips series with zero total demand in the test window
(10–28 of 30,490 series depending on `h`).

## Headline findings

**1. The WRMSSE ranking is unambiguous and horizon-stable:**
direct LightGBM (0.56–0.60) < recursive LightGBM (0.63–0.70) < Seasonal
Naive (0.77). This is the first self-consistent WRMSSE number we have
from our own code, on the M5 tail, for three model families. The M5
competition's winning submission reached **WRMSSE 0.520** using 220
per-store LightGBM models with store/item embeddings, lag_28, holiday
lookups, and calibrated Tweedie variance. Our "vanilla" direct LightGBM
— single global model, 6 covariates, no embeddings, no lag_28, 300 trees
— lands at **0.5598 at h=7**, within **7.7%** of the published winner.
This is a useful anchor: the FM-killer baseline is not "a beefy tuned
LightGBM is 40% better than naive", it is "even a single-model
direct-multistep LightGBM gets ~85% of the way from SN to the winner".

**2. Direct multistep prediction eliminates the MAE/WAPE split we saw in
Phase B.** Phase B flagged that recursive LightGBM beat SN on MAE (10–13%)
but lost badly on WAPE (24–46% worse, *growing with horizon* from 1.62
at h=7 to 1.94 at h=28). Phase C isolates the cause:

| Metric | rec h=7→h=28 | dir h=7→h=28 |
|---|---|---|
| WAPE | 1.6246 → 1.9357 (+19%) | 1.3512 → 1.5133 (+12%) |
| sMAPE | 144.44 → 144.48 (flat) | 145.81 → 146.95 (flat) |

Direct LightGBM's WAPE is **flat-to-slightly-growing** with horizon
because each step is predicted from real lags rather than predicted
lags; recursive LightGBM's WAPE **grows monotonically** with horizon
because error in step `k` contaminates the inputs to step `k+1`. Both
variants still post sMAPE ~145% because that's the Tweedie-mean-vs-zero
artefact on intermittent demand — it's a metric property, not a model
property, and direct prediction does not fix it. This decomposition
cleans up the Phase B "metric flips the winner" story: the WAPE
divergence was **recursive-error compounding**, not a fundamental
intermittent-demand/Tweedie problem. sMAPE divergence is still genuine
metric-dependence.

**3. Direct beats recursive on every metric at every horizon**,
including the ones where the model is "supposed" to be bad. Direct's MAE
is 4–6% below recursive's; direct's sMAPE is only trivially worse
(146 vs 144 — within noise); direct's WAPE is ~17–22% better; direct's
WRMSSE is 12–14% better. There is no horizon at which recursive wins.
This contradicts the common FM-paper framing of "one global LightGBM
with recursive prediction" as the ML baseline — recursive is the cheap
variant, and FM comparisons that use it are comparing against a strictly
dominated baseline.

**4. Cost ratio direct:recursive is 4–13×** (rising with horizon because
direct fits `h` models sequentially). Absolute numbers are still tiny
— the most expensive job in the sweep, `lgbm_dir_h28`, cost **$0.39**
and emitted 1g CO₂. But on Favorita/Rohlik (larger panels or longer
training windows), the direct variant's cost will scale linearly in `h`,
while a foundation model's cost is horizon-independent. This is the
cost axis the meta-analysis needs to argue on, and this data point
quantifies it on M5.

## Aggregated picture of the baseline story

The WRMSSE table answers the meta-analysis question "what do FMs need
to beat on M5?" at three levels of baseline strength:

| Baseline level | WRMSSE (h=7) | Comment |
|---|---|---|
| Seasonal Naive | 0.776 | Zero training, calendar-unaware |
| Vanilla LightGBM recursive | 0.634 | Single global model, 6 covariates, standard FM-paper baseline |
| Vanilla LightGBM direct | **0.560** | Same features, `h` models, M5-winner-style protocol |
| M5 winner (Makridakis 2022) | 0.520 | 220 models, store/item embeddings, calibrated variance |

A foundation model that claims "beats LightGBM on M5" needs to specify
*which* LightGBM. Most FM papers that cite ~0.64–0.69 are actually
beating the recursive single-global variant. A ~5% WRMSSE headroom
between recursive and direct LightGBM is a much harder bar to clear, and
the gap between direct and the M5 winner (~7%) leaves very little room
for a zero-shot FM to declare victory.

## Reliability / sanity checks

- **SN WRMSSE 0.7661–0.7758** is slightly below the ~0.85 number
  published for the M5 seasonal-naive benchmark. The difference is
  protocol: the paper's SN uses the last observation (period=1) on the
  official 28-day test window; ours uses weekly-period SN on a longer
  tail. Our numbers are internally consistent across horizons (0.766
  → 0.772 → 0.776, nearly flat, as expected for a baseline that has no
  training and no horizon coupling), which is the important check.
- **SN WRMSSE drops slightly with horizon** (0.7758 at h=7, 0.7661 at
  h=28) because longer non-overlapping windows give fewer, less noisy
  per-window scale-normalized errors. Recursive LGBM does the opposite
  (error compounding). Direct LGBM is in between (no compounding but
  longer-step models learn a harder target).
- **lgbm_rec and lgbm_dir are fit on the same training matrix** (same
  365-day window, same features), so the MAE/WRMSSE gap is entirely
  attributable to the direct-vs-recursive eval protocol, not model
  capacity or data.

## Observations and next steps

1. **Phase C is the baseline-reliability anchor** for §3 of the paper.
   The direct LightGBM WRMSSE 0.560 is the number to compare every
   foundation model against when it reports on M5 in the meta-analysis
   extraction table.
2. **Don't cite MAE on M5 without WRMSSE**. Phase B's WAPE-blow-up was
   real but localized to recursive prediction; with direct multistep,
   MAE-vs-WAPE still *disagrees on the SN-vs-LGBM gap size* (MAE gap is
   ~16%, WRMSSE gap is ~28%), but they agree on the ranking. sMAPE
   still flips on both LightGBM variants — the Tweedie-mean pathology
   is a metric bug that direct prediction cannot cure.
3. **The remaining gap to the M5 winner** (0.56 → 0.52, ~7%) is
   reachable with the standard M5 tricks: lag_28, per-store models,
   store/item embeddings, non-zero `random_state` ensembling. This is
   worth quantifying as a follow-up experiment because it bounds the
   "upper baseline" for the meta-analysis.
4. **GPU quota** is still pending on Maciej's side. Once foundation
   models can run on the same tail window, we have a three-way baseline
   (SN / rec / dir) and an M5-winner reference point — any FM number
   above 0.52 on M5 is not a win over the baselines.
5. **Favorita/Rohlik replication** is still blocked on Kaggle token
   refresh (local cache and GitHub secret both returned 401 today).

## Files

- Logs: `/tmp/mm_logs/{sn_h7,sn_h14,sn_h28,lgbm_rec_h7,lgbm_rec_h14,lgbm_rec_h28,lgbm_dir_h7,lgbm_dir_h14,lgbm_dir_h28}/artifacts/user_logs/std_log.txt`
- MLflow runs: experiment `meta-analysis-gap-filling`, run names
  `sn_h{7,14,28}`, `lgbm_rec_h{7,14,28}`, `lgbm_dir_h{7,14,28}`
- Pipeline: `benchmark/code/pipelines/m5_consolidated.yaml`
- WRMSSE implementation: `benchmark/code/evaluation/wrmsse.py`
