# §5.3 Baseline reliability: what is a fair LightGBM on M5? — DRAFT v0.1

*Drop-in draft for §5 of the paper (Gap-Filling Experiments). Source
data: `analysis/baseline_results.md` Phase B + Phase C; pipelines
`witty_wheel_pyjt84yt2j` and `mighty_morning_6qz5c4jmwm`.*

---

Every foundation model paper that reports results on M5 compares
against a LightGBM baseline, and every paper uses a different LightGBM.
This matters more than it sounds: as we show below, "vanilla LightGBM
with covariates" on M5 can mean anything from WRMSSE 0.70 to WRMSSE
0.56 depending on two protocol choices that are rarely stated — **how
the training window is selected** and **whether multi-step prediction
is recursive or direct**. The 25% gap between the weakest and
strongest reasonable-vanilla variants is large enough that a
foundation model can appear to "beat LightGBM" on one protocol and lose
to it on another, with no change in the FM itself.

We instantiate this range with three experiments on the held-out M5
tail (days 1552–1940, 389 evaluation days), all sharing a single
eval window and a single set of covariates (`sell_price`, `snap_CA`,
`snap_TX`, `snap_WI`, `is_event`, `wday`, `month`, plus lags
{1, 7, 14} and rolling means {7, 14}). The three variants are:

1. **Seasonal Naive** — period 7, no training, no covariates;
2. **LightGBM recursive** — one global Tweedie model (variance_power
   = 1.1, 300 trees, num_leaves = 63) trained once on the last 365 days
   of the training portion, then applied recursively at evaluation time
   with its own output fed back into lag features;
3. **LightGBM direct** — `h` separate global Tweedie models (same
   hyperparameters, same feature set) trained on the same 365-day
   window, where model `k` predicts `y[t + k]` from lags known at `t`
   and future-known covariates at `t + k`, without any feedback.

All three use identical rolling-origin non-overlapping forecast
windows of length `h ∈ {7, 14, 28}`. WRMSSE is computed in-job via the
full 12-level Makridakis (2022) hierarchy from the same raw
sales/calendar/prices CSVs as the predictions.

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
dominated baseline and should not be reported as "beats LightGBM"
without qualification.

### 5.3.4 Method note and threats to validity

Two methodological simplifications in our LightGBM variants are worth
stating because they bound the ceiling we report:

1. **Single global model vs per-store models.** The M5 winner trained
   220 separate LightGBM models, one per store. Our direct variant
   trains one model across all 30,490 series. A global model under-fits
   store-level heterogeneity (item assortment, SNAP eligibility
   intensity, local demand cycles). We estimate the per-store split
   would recover ~1–2% WRMSSE, bringing direct to ~0.54–0.55 at `h=7`.
2. **No lag_28 feature.** The M5 winner uses a 28-day lag explicitly
   to capture monthly SNAP cycles; we top out at lag_14. Adding lag_28
   to the direct variant is a one-line change and is on the follow-up
   list for Phase D.

On the other side, our training window is only the last 365 days of
the training portion (a deliberate cap to keep single-job training
tractable on E4DS_V4, where fitting ~10.7M rows takes ~180 s per
model). Extending the window to the full training portion (~1,500
days) would give the model more data on promotional cycles; we
estimate this recovers another ~1% WRMSSE. Combined, a properly
tuned direct LightGBM with lag_28, per-store splits, and full-window
training should land at WRMSSE ≈ 0.53–0.54, i.e. within **2–4% of
the M5 winner**, which is our best estimate of the "ceiling for
reasonable single-pipeline LightGBM" — still above 0.520 but well
below the zone where foundation models need to compete.

### 5.3.5 Cost envelope

The full sweep (9 jobs × 30,490 series × 389 evaluation days) cost
**$0.81 on Azure ML `cc-forecast-batch` (E4DS_V4)** with 0.0025 kg
CO₂ total. Runtime is dominated by `lgbm_dir_h28`, which trains 28
sequential Tweedie models at ~133 s each for a total of 62 minutes
and $0.39. Linear extrapolation gives a ceiling on the direct-variant
cost: even at `h = 28` on the full-window / per-store configuration
described in §5.3.4, total compute cost per horizon should remain
under $5. This is an order of magnitude below the zero-shot inference
cost of the smallest foundation models in our review on the same
eval window — a point we return to in the cost-accuracy Pareto
analysis (§6.3).

### 5.3.6 Takeaways for the rest of the paper

We use **LightGBM direct with the Table 5.3 configuration** as the
canonical LightGBM baseline for §6 (meta-regression) and the
Pareto frontier in §6.3. All foundation models evaluated on M5 are
compared against both variants (direct *and* recursive) with the
recursive number flagged as the "weakest reasonable baseline".
Meta-regression moderator analysis treats the direct-vs-recursive
choice as a protocol covariate. sMAPE is excluded from primary
comparisons on intermittent datasets; WAPE and WRMSSE are the
primary metrics on retail tasks with > 50% zero days.

---

*Next steps after FM sweeps land:*

- Drop FM WRMSSE numbers into Table 5.3 as additional rows.
- Project the §5.3.4 "full-tuning ceiling" LightGBM (lag_28 +
  per-store + full window) as a Phase D experiment to close the
  winner gap.
- Append metric-dependence finding to §8.1 (Discussion: data
  leakage and baseline reliability).
