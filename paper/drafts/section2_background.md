# §2 Background

Short-term retail demand forecasting — predicting daily or weekly
SKU-level sales 1–4 weeks ahead — is one of the most mature applied
forecasting problems. The operational stakes (replenishment, markdown
optimisation, labour scheduling) have driven a long lineage of
benchmark competitions and model development. This section
establishes the taxonomy we use throughout the paper and surveys the
three benchmark ecosystems whose results populate our extraction
schema.

### 2.1 Taxonomy of forecasting approaches

We group methods into four families, matching the `model_family`
field in our extraction schema (§3.2). The grouping is coarse by
design: the meta-regression (§6) treats it as a categorical
moderator, so finer distinctions (e.g., GRU vs Transformer within
NN) would create sparsely populated cells.

**Statistical models.** Exponential smoothing (ETS), ARIMA, Theta,
Seasonal Naive, and intermittent-demand methods (Croston, TSB). These
are fitted per-series with no cross-series learning. Their value in
this paper is as a sanity-check baseline: any global model that loses
to Seasonal Naive on a given (dataset, horizon) cell is failing in a
way that demands explanation, not hand-waving. We include Croston
because M5 has a ~70 % zero-day fraction and Croston is the textbook
method for intermittent demand. In our extraction schema these models
carry `model_family = "statistical"`.

**Gradient-boosted trees (ML_TREE).** LightGBM and XGBoost fitted as
global models: one model trained across all series, with
cross-sectional features (lags, calendar effects, price, promotions,
store/item embeddings). This is the family that the M5 competition
(§2.2) crowned as the winner, and it remains the production default at
most retailers. In the extraction schema, `model_family ∈
{"ml_tree", "ml", "ml_gbm", "gbdt", "ml_ensemble", "ml_hybrid"}`.
The §5.3 baseline reliability analysis shows that the choice of
multi-step strategy (direct vs recursive) within this family can flip
the accuracy ranking by 10+ pp WAPE depending on demand distribution
— a confound that the literature rarely reports and that our
gap-filling experiments control for.

**Deep learning (NN).** Recurrent (DeepAR, LSTNet), attention-based
(TFT, PatchTST, Informer), and MLP-based (N-BEATS, N-HiTS) models
trained on many series. These models occupy a middle ground: they
learn cross-series patterns like tree models but have higher
computational cost and typically require more data to avoid
overfitting. In the M5 competition, the top-50 solutions were
overwhelmingly tree-based; DL entries placed in the top quartile but
did not win outright. Since 2023, PatchTST and its descendants have
narrowed the gap on benchmark suites. In the extraction schema,
`model_family ∈ {"nn", "deep", "transformer", "rnn",
"deep_learning", "ensemble_dl"}`.

**Foundation models (FM).** Pre-trained on large corpora of
heterogeneous time series and applied zero-shot (no fine-tuning on
the target dataset) or with lightweight fine-tuning. The models in
scope for this review are:

| Model | Params | Architecture | Covariates | Key reference |
|-------|-------:|-------------|:----------:|---------------|
| Chronos / Chronos-2 | 9–710 M | Encoder-only T5 | v2 only | Ansari et al. (2024, 2025) |
| TimesFM 2.5 | 200 M | Decoder-only | No | Das et al. (2025) |
| Moirai 2.0 | 14–300 M | Masked encoder | Yes | Woo et al. (2025) |
| TiRex | ~35 M | xLSTM | No | Gruber et al. (2025) |
| TabPFN-TS | ~12 M | Tabular PFN + TS head | No | Müller et al. (2025) |
| Lag-Llama | 6 M | Llama backbone | No | Rasul et al. (2024) |
| TimeGPT | undisclosed | Proprietary | Yes | Garza & Mergenthaler-Canseco (2023) |

In the extraction schema, `model_family = "foundation"`. The
zero-shot setting is the primary scope of this review; fine-tuned FM
entries (e.g., Chronos-2 with in-domain pre-training) are retained in
the schema but flagged as `fine_tuned = "Yes"` and excluded from the
primary meta-regression to avoid confounding pre-training scale with
task-specific tuning.

### 2.2 Existing benchmarks

Three benchmark ecosystems contribute the majority of our extraction
rows. We note their design choices because those choices determine
what the extracted metrics actually measure — and where they
systematically mislead.

**M5 Competition (Makridakis et al., 2022).** 30,490 daily Walmart
series across 10 stores and 3,049 products, with calendar, price,
and SNAP covariates. The official metric is WRMSSE — a weighted
ratio of root mean squared scaled errors that accounts for
intermittent demand by scaling each series' error by its historical
variability. The competition was won by gradient-boosted trees (top-5
all LightGBM or XGBoost); the best DL entry (DeepAR) placed around
#50. M5 is still the go-to retail benchmark in 2026, but it has two
ageing problems: (1) the data is from 2011–2016, predating modern
promotional patterns, and (2) many foundation model papers report
per-series WAPE rather than WRMSSE on M5, creating a metric mismatch
that §5.4.5 documents in detail. On per-series WAPE, the ~70 %
zero-day fraction in M5's long tail causes denominator explosions
that make LGBM appear to perform worse than Seasonal Naive — a metric
artefact, not a model failure.

**GIFT-Eval (Aksu et al., 2024).** 28 datasets (144,879 series)
curated to avoid train–test leakage in foundation-model evaluations.
Covers multiple domains including retail, energy, and transport. The
standard metric is a skill score relative to Seasonal Naive,
computed with bootstrapped confidence intervals. GIFT-Eval is the
dominant evaluation suite in the FM literature: most of our Category A
(FM paper) rows cite it. Its limitation for our purposes is that only
a subset of the 28 datasets is retail-specific, and the aggregate
skill scores mix retail with non-retail, making it hard to extract a
clean retail-only FM-vs-ML_TREE delta.

**fev-bench (Bochenek et al., 2025).** 100 tasks spanning 46 with
exogenous covariates, designed as a direct response to the "no
covariates in FM evaluation" criticism. Uses bootstrapped CIs and
skill scores. Covers a broader set of model families than GIFT-Eval,
including covariate-aware baselines that are largely absent from FM
papers. For our extraction, fev-bench provides the largest single
block of rows with both FM and statistical baselines on the same
tasks, though the task-level granularity (rather than dataset-level)
makes cross-benchmark alignment non-trivial.

### 2.3 Meta-analyses in forecasting

The M-competition lineage (M1–M5, Makridakis 1982–2022) is the
closest antecedent to our work: each competition is, in effect, a
large-scale empirical comparison of forecasting methods on a shared
dataset with standardised metrics. The M5 (retail) and M4
(heterogeneous) competitions produced substantial secondary analysis,
but always on a single dataset per competition. Petropoulos et al.
(2022) survey the forecasting landscape broadly but do not run a
PRISMA-compliant meta-regression. Lim & Zohren (2021) review deep
learning for time series but predate the FM wave.

To our knowledge, **no prior work combines** (1) a PRISMA-compliant
systematic search, (2) quantitative extraction across multiple
benchmarks, (3) gap-filling experiments to fill structural holes, and
(4) a random-effects meta-regression with moderators — for
foundation models in the retail forecasting domain. This is the gap
we fill.
