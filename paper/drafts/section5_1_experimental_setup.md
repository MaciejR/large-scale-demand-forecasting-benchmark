# §5 Gap-Filling Experiments

## §5.1 Experimental Setup — DRAFT v0.1

*Drop-in draft for §5.1 of the paper (Gap-Filling Experiments —
Setup). This section defines the shared protocol used across
Phases B–F. The section is deliberately short and self-contained;
dataset-specific deviations are noted inline where they occur, and
the cross-dataset analysis lives in §5.3.*

---

All gap-filling experiments described in §5 follow a single
experimental protocol, parameterized per dataset. This section
defines the protocol once. Dataset-specific choices (covariate
sets, eval-window lengths, series-count caps) are noted inline in
§5.2 for baseline models and §5.4 for foundation models.

### 5.1.1 Datasets

We evaluate on three retail demand forecasting datasets, chosen
to span the distribution of zero-day fractions in public retail
benchmarks while keeping the hierarchical-SKU × location
structure that retail practitioners actually face. The three
datasets together cover ~211k × 1.4k series-days across the full
product × location × time tensor.

**Table 5.1.** Datasets used in the gap-filling experiments.
`Zero-day fraction` is the fraction of series-day observations
with `y = 0` in the training portion, a core moderator variable
in §6.

| Dataset   | n_series (full) | n_series (used) | n_days | Frequency | Zero-day frac | Covariates used |
|---|---|---|---|---|---|---|
| M5        |  30,490 |  30,490 | 1,941 | daily | ~70 %   | sell_price, snap_CA/TX/WI, is_event, wday, month |
| Rohlik v2 |   5,390 |   5,390 | 1,402 | daily | ~1.2 %  | sell_price_main, holiday, shops_closed, winter_school_holidays, school_holidays, dayofweek, month |
| Favorita  | ~174,685 | 30,000 | 1,684 | daily | ~15–25 %, long tail | onpromotion, dcoilwtico, is_holiday, transactions, dayofweek, month |

Three notes on dataset preparation:

- **M5** is used in full. The 30,490 store-item series correspond
  to the Walmart subset of the M5 competition (Makridakis et al.
  2022); we use the official tail 389 days as the evaluation window
  (§5.1.3).
- **Rohlik v2** is used in full. The dataset is 5,390
  warehouse-SKU series from the Kaggle competition `rohlik-sales-
  forecasting-challenge-v2`, covering 2020-08-01 to 2024-06-02
  across 7 warehouses (Prague ×3, Brno, Munich, Frankfurt,
  Budapest). Approximately 31% of Rohlik SKUs enter later than
  day 1 (ragged series starts), which we handle at the wide-pivot
  step via `fillna(0)` — see §5.1.4.
- **Favorita** is capped at the top 30,000 series by total
  `unit_sales` across the training portion, matching M5's scale
  for cross-dataset forecast-count comparability. The full
  dataset has ~174,685 series at ~125 M rows and does not fit the
  32 GB E4DS_V4 compute used for Phases A–D. The selection rule
  biases Favorita LightGBM evaluation toward higher-velocity
  series; this is flagged as a limitation in §5.3.7 and §7, and
  the full-series evaluation is scheduled for Phase F on larger
  hardware.

All three datasets are registered as versioned Azure ML data
assets (`azureml:m5-sales:1`, `azureml:rohlik-train-v2:1`,
`azureml:favorita-train:1`, plus per-dataset covariate assets)
for exact reproducibility.

### 5.1.2 Compute and tracking

All jobs run on Azure ML compute cluster `cc-forecast-batch`
(E4DS_V4 VM, 4 vCPU / 32 GB RAM / no GPU) in region
`swedencentral`, inside Docker environment
`forecast-benchmark-cpu-env:1`. We use `cc-forecast-batch` for
the classical and ML baselines of §5.2–§5.3. Foundation model
sweeps (§5.4) will use a GPU-backed cluster once quota is
approved; setup for Phase F is documented in the reproducibility
appendix.

Experiment orchestration uses Azure ML pipelines defined in
`benchmark/code/pipelines/{m5,rohlik,favorita}_consolidated.yaml`.
Every run logs metrics, parameters, runtime, and per-series CSVs
via MLflow to the workspace tracking server. Cost and CO₂
estimates are computed inside the job using Azure's published
per-second pricing for `Standard_E4ds_v4` in `swedencentral`
(`$0.38/hr` at time of writing) and the region's marginal CO₂
intensity (0.274 kgCO₂eq/kWh, swedencentral 2025 baseline). The
per-job runtime, cost, and CO₂ columns in Tables 5.3–5.5 are
computed this way and are therefore comparable across datasets.

### 5.1.3 Evaluation protocol

For each dataset we use **rolling-origin non-overlapping
evaluation with a held-out tail window**, which is the protocol
most commonly used in the FM papers we screened (§4) and which
gives a clean, reviewer-auditable split. Specifically:

- **Train / eval split:** `train_until = floor(0.8 × n_days)`.
  This gives a tail-eval window of 389 days on M5, 281 days on
  Rohlik, and 337 days on Favorita. The choice of 0.8 follows
  Hewamalage et al. (2022) and Shchur et al. (fev-bench, 2025).
- **Rolling origin:** within the tail window, forecast origins
  are spaced exactly `h` days apart so that windows are
  non-overlapping. For example at `h = 14` on Rohlik (eval
  window = 281 days), we have `floor(281/14) = 20` evaluation
  windows per series. This keeps per-horizon sample counts
  independent of each other and avoids the optimistic bias of
  overlapping-windows evaluation.
- **Horizons:** `h ∈ {7, 14, 28}` on all three datasets. Seven
  days is the operational horizon most retailers use for
  short-term replenishment; 28 days is the M5 competition
  horizon and a common upper bound in the literature (Makridakis
  et al. 2022); 14 days bridges the two. We report every metric
  at every horizon to enable horizon-conditioned interpretation.
- **Metrics:** MAE, sMAPE, WAPE, and (on M5 only) WRMSSE. MAE
  and WAPE are computed per series and averaged with equal
  weights (`_mean` suffix in the tables). sMAPE uses the
  classical symmetric form with a 200% cap on zero actuals.
  WRMSSE is computed in-job via the full 12-level Makridakis
  (2022) hierarchy from the raw sales/calendar/prices CSVs. On
  retail tasks with heavy right tails (all three of ours), sMAPE
  is reported only for reproducibility and is not used in any
  primary comparison — see §5.3.9 for the cross-dataset
  justification.
- **Per-series filtering for WAPE:** WAPE requires a non-zero
  denominator (sum of actuals in the eval window). For series
  where the denominator is zero we drop the series from WAPE
  computation and report the `n_valid` count alongside the
  metric in Tables 5.3–5.5. This affects at most 0.5 % of M5
  series and a higher fraction on Rohlik (where ragged starts
  leave some series with only a few eval-window days); on
  Favorita the fraction is negligible for LGBM and ~50 % for
  SN, an n_valid asymmetry we discuss in §5.3.5.

**Sampling adequacy of n = 100 series per cell.** Source B FM
cells sample 100 series per cell (98–100 after WAPE filtering).
To verify that this sample size produces stable WAPE estimates,
we ran a 10,000-iteration bootstrap on all 18 FM per-series CSV
files. The bootstrap standard error of mean WAPE across cells
ranges from 0.008 (Favorita h = 7) to 0.014 (Rohlik h = 28),
with a median of 0.011. The widest 95 % bootstrap CI is
±0.027 WAPE (Rohlik h = 28). This means: (a) the M5 FM-vs-LGBM
gap of 40+ pp WAPE is stable to >10 SE; (b) the Rohlik gap of
4–8 pp is stable to 3–6 SE; (c) the Favorita "close call" of
0.3 pp at h = 7 is within 1 SE and should be interpreted as
indistinguishable from zero at n = 100 — consistent with the
meta-regression finding (§6.7). Full bootstrap results are in
`analysis/figures/table_bootstrap_se.csv`.

### 5.1.4 Model families

Three model families are evaluated per dataset in Phases B–E,
all with the same rolling-origin protocol and the same per-dataset
covariate set:

- **Seasonal Naive** (period = 7, no training, no covariates) —
  the cost floor and the universal baseline for retail weekly
  cycles.
- **LightGBM recursive** — one global Tweedie model per dataset,
  fit with `variance_power = 1.1`, 300 boosting rounds,
  `num_leaves = 63`, minimum child samples = 20, learning rate
  0.05, `feature_fraction = 0.8`, `bagging_fraction = 0.8`. The
  model uses lags {1, 7, 14}, rolling means {7, 14}, and the
  dataset-specific covariates listed in Table 5.1. At evaluation
  time, the model is applied recursively: predictions at step `k`
  enter the lag features for step `k + 1`, and future-known
  covariates are passed through unchanged.
- **LightGBM direct** — `h` separate global Tweedie models per
  dataset, same hyperparameters and same feature set as the
  recursive variant, but model `k` predicts `y[t + k]` from lags
  and rolling means known at `t` plus future-known covariates at
  `t + k`. No output feedback, no recursion.

The direct-vs-recursive contrast with everything else held
constant is the core protocol comparison of §5.3. Hyperparameters
are intentionally untuned beyond library defaults: the point of
§5.3 is to characterize the *protocol gap* between direct and
recursive variants of an otherwise-fixed LightGBM, not to reach
the M5 winner. Ceiling projections for tuned LightGBM are
discussed in §5.3.7.

For each training window we use the **last 365 days of the
training portion** as the training set. This cap is a deliberate
scalability choice — fitting ~10–30 M rows per LightGBM model
takes 180–240 s on E4DS_V4 — and we estimate in §5.3.7 that
extending to the full training portion would recover ~1 % on
WRMSSE on M5. The same cap applies on Rohlik and Favorita for
comparability.

Foundation models (Chronos-Bolt, Chronos-2, TimesFM 2.5, Moirai
2.0, TiRex, TabPFN-TS) are evaluated zero-shot in Phase F on the
same rolling-origin protocol, using each model's published
inference script. Details of the FM protocol, context-length
choices, and the GPU cluster configuration are in §5.4.

### 5.1.5 Reproducibility

Every result reported in §5.2–§5.3 is tied to:

- **A git commit** — the commit SHA appears in the per-job MLflow
  run and in the caption of each results table.
- **An Azure ML pipeline run name** — these are the `mighty_*`,
  `goofy_*`, and `loyal_*` job names referenced in the table
  captions (§5.2, §5.3). Every job can be re-invoked exactly
  from the pipeline YAML and the registered data asset version.
- **A registered data asset version** — `azureml:m5-sales:1`,
  `azureml:rohlik-train-v2:1`, `azureml:favorita-train:1`, plus
  per-dataset covariate assets. Data is immutable once registered;
  the `:1` suffix binds the job to the exact snapshot.
- **A versioned environment** — `forecast-benchmark-cpu-env:1`
  (and `:2` for Phase F GPU jobs). The environment specifies
  Python 3.11, `lightgbm==4.6.0`, `pandas==2.2.0`, `numpy<2`,
  and the loader code path.

Code and data-asset manifests are released in the paper's
reproducibility appendix and at the repository linked in §9.

---

*Sources for this section:* `benchmark/code/pipelines/*.yaml`,
`benchmark/code/experiments/run_gap_filling.py`, `analysis/
baseline_results.md` (§5.2 draws its numbers from the same files).
