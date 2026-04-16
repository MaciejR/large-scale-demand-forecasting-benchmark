# §7 Decision Framework

The meta-regression of §6 answers "when do FMs pay off?" in
statistical terms (Δ̂, CIs, moderator directions). This section
translates those findings into a practitioner-oriented decision
tool: given a retail team's data characteristics and infrastructure
constraints, which model family should they evaluate first?

### 7.1 The decision tree

The framework is a three-question flowchart. Each leaf recommends a
starting model family and flags the dominant risk.

```
Q1: Does your dataset have >15% zero-day fraction
    (intermittent / sparse demand)?
│
├── YES → Q2a: Do you need per-series point-forecast accuracy
│         (e.g., replenishment at SKU level)?
│         │
│         ├── YES → START WITH: LightGBM direct + covariates
│         │         WHY: On intermittent data, direct LGBM wins
│         │         by 17–22% over recursive (§5.3.6 Table 5.8),
│         │         and per-series WAPE is unreliable as a metric
│         │         (§5.4.5). Use WRMSSE or aggregate WAPE for
│         │         model selection. FMs post lower per-series
│         │         WAPE but this is a metric artefact, not a
│         │         real accuracy gain (§6.7 M5 finding).
│         │         RISK: Per-series WAPE will mislead you into
│         │         picking the FM. Validate on WRMSSE.
│         │
│         └── NO (aggregate-level forecast, e.g., category
│              planning) → START WITH: FM zero-shot
│              WHY: At the aggregate level, FM and LGBM converge
│              (aggregate WAPE ratio ~0.89, §5.4.5). The FM
│              requires no feature engineering, saving 2–4 weeks
│              of data pipeline work.
│              RISK: No covariate channel in most FMs — if
│              promotions drive >20% of variance, LGBM wins.
│
└── NO (smooth / continuous demand, <15% zero-day) →
    Q2b: Do you have rich covariates (promotions, price,
         calendar events) AND engineering capacity to build
         a feature pipeline?
         │
         ├── YES → START WITH: LightGBM recursive + covariates
         │         WHY: On Favorita (covariate-rich, smooth
         │         demand), lightgbm_cov matches Chronos-Bolt-
         │         Tiny within 0.3 pp WAPE at h=7 and beats it
         │         at h=14,28 (§5.4.5). Recursive outperforms
         │         direct by 4–10% on smooth demand (§5.3.6).
         │         The FM adds no accuracy and costs more in
         │         inference latency at scale.
         │         RISK: Feature engineering is the bottleneck,
         │         not model selection. Budget 60% of effort on
         │         features, 20% on tuning, 20% on evaluation.
         │
         └── NO (limited covariates or no feature engineering
              capacity) → Q3: Is wall-time latency critical
              (e.g., <5 min for 10K series)?
              │
              ├── YES → START WITH: Chronos-Bolt-Tiny
              │         WHY: 9M params, ~0.6s per series on
              │         consumer CPU, competitive with LGBM
              │         on Rohlik within 4–8 pp WAPE (§5.4.7
              │         Table 5.9). No feature pipeline needed.
              │         RISK: On Rohlik h=28, seasonal_naive
              │         overtakes lightgbm_cov (0.412 vs 0.432)
              │         — at long horizons on smooth data, even
              │         naive beats a poorly tuned tree.
              │
              └── NO → START WITH: TiRex
                        WHY: Beats Chronos-Bolt-Tiny on all 9
                        paired cells by 0.6–2.3 pp (§5.4.5),
                        at ~3.5× the FLOPs. Worth the cost when
                        wall time is not binding and 1 pp WAPE
                        matters for the business case.
                        RISK: MPS xLSTM stall on Apple silicon
                        (§5.4.9). Use TIREX_FORCE_CPU=1 or
                        deploy on CUDA.
```

### 7.2 Cost thresholds

The decision tree above is accuracy-first. When cost is the binding
constraint, the §6.5 Pareto analysis adds a second dimension.

**Consumer hardware (MacBook M-series MPS).** The 18 FM Source B
cells ran in ~10.3 h wall time at $0.062 marginal electricity
(Polish grid) and 0.201 kg CO₂. Per 1,000 series per horizon, FM
inference costs ~$0.003 and emits ~0.011 kg CO₂. This is 16×
cheaper in $ than the Azure E4DS_V4 batch baseline ($0.048 per
1,000 series) but 44× higher in CO₂ per $ (the Azure grid is
Swedish hydro, ~0.02 kg CO₂/kWh vs Poland at ~0.7 kg CO₂/kWh).

**When the FM "pays off" in $ terms:**
- If the team already has a consumer MacBook and no cloud budget,
  FM inference is essentially free (marginal electricity only) and
  the accuracy delta on smooth-demand data is <1 pp WAPE. The FM
  pays off immediately.
- If the team has cloud infrastructure and a data engineering team,
  the FM saves ~2–4 weeks of feature pipeline work but adds
  inference latency. The break-even is at ~50 forecasting runs:
  below 50 runs the saved engineering time dominates; above 50 runs
  the per-run LGBM cost savings dominate.

**When the FM does NOT pay off:**
- On intermittent-demand data where per-series accuracy matters and
  WRMSSE is the evaluation metric: the FM posts 0.97 WRMSSE vs
  competition-grade LGBM at 0.52 on M5. No cost argument overcomes
  a 45 pp accuracy gap on the business-relevant metric.
- When the team has rich covariates that carry real signal
  (promotions, markdown schedules, weather): univariate FMs cannot
  access this information and the covariate-aware LGBM baseline
  consumes it directly.

### 7.3 Recommendations by role

**Data scientist / ML engineer** evaluating model families for a new
retail forecasting system:
1. Profile your demand distribution: compute zero-day fraction per
   series. If median > 15%, you are in the intermittent regime and
   LGBM direct is the default.
2. Run Seasonal Naive as a sanity floor. Any model that loses to it
   on a given (dataset, horizon) cell is broken.
3. If smooth demand and no covariates: try Chronos-Bolt-Tiny
   zero-shot. If it lands within 2 pp WAPE of your internal
   baseline, ship it — the engineering savings justify the gap.
4. If smooth demand and rich covariates: invest in LightGBM
   recursive with a proper feature pipeline. The FM will not beat
   it and will not use your covariates.

**Engineering manager** sizing infrastructure:
- Consumer-HW FM inference (MacBook, no GPU) is viable for datasets
  up to ~30K series with daily re-forecasting. Above that, batch
  on cloud CPU (E4ds_v4-class) is cheaper than renting GPUs, and
  LGBM on the same CPU instances is faster per series.
- GPU allocation for FM inference is not justified on any of our
  three retail datasets — the accuracy delta does not warrant the
  cost premium over CPU inference.

**VP / Director** making a build-vs-buy decision:
- The FM "pays off" when your team does not have the bandwidth to
  build and maintain a covariate feature pipeline. The accuracy
  sacrifice on smooth-demand data is <1 pp WAPE (Table 5.9,
  Favorita row) — likely within the noise floor of most business
  KPIs.
- The FM does NOT pay off when you already have a production LGBM
  pipeline with promotions and calendar features: swapping to an
  FM loses the covariate signal with no accuracy gain.
