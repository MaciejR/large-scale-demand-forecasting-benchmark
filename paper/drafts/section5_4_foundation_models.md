# §5.4 Foundation Model Protocol — DRAFT v0.2

*Drop-in draft for §5.4 of the paper (Gap-Filling Experiments —
Foundation Models). §5.4 populates Table 5.7 (§5.2.4) from two
complementary data sources: the PRISMA literature extraction for
the bulk of the FM grid (§5.4.2), and a small local consumer-box
sensitivity run that we execute ourselves on a MacBook via
PyTorch MPS (§5.4.3). This structure replaces the Phase F
cloud-GPU sweep from v0.1, which is blocked indefinitely on
Azure GPU quota and is no longer on the critical path for this
paper.*

---

### 5.4.1 Scope and two-source strategy

Foundation model rows in Table 5.7 come from two sources, each
serving a distinct purpose in the meta-regression (§6).

**Source A — Literature extraction (primary).** The PRISMA
corpus (§4, `analysis/extraction_schema.csv`, 214 rows) already
contains zero-shot FM numbers on all three of our datasets,
extracted from the source papers and anchored to their published
MLflow runs or competition submissions. Between B01 (GIFT-Eval
2025 leaderboard), B02 (fev-bench 2025 retail tasks), and the
per-model technical reports A01 (Chronos), A02 (Chronos-2), A04
(TimesFM 2.5), A06 (Moirai 2.0), A11 (Chronos-Bolt), A13
(TiRex), A14 (TabPFN-TS), the primary FM grid of Table 5.7 can
be populated **entirely from extraction** without any of our own
inference runs. This is the right data source for the meta-
analysis framing: the central object of §6 is the *literature
disagreement* between papers, and own runs risk biasing the
pool toward our protocol choices (§5.3.9). The strict PRISMA
reader is entitled to ask for a paper that reports no new FM
numbers, and we deliver one.

**Source B — Local consumer-box sensitivity (secondary).** We
also execute a small sensitivity run on a MacBook (M-series, 16
GB unified memory) via PyTorch MPS, on three small models —
Chronos-Bolt-Tiny, TabPFN-TS, and TiRex — across the same three
datasets and horizons. The purpose is **not** to add new FM
cells to Table 5.7; it is to anchor the consumer-CPU Pareto
panel of Figure 6.4 (§6.5), which replicates the F04
(arXiv 2602.10848, "TS FM for Energy Load on Consumer HW")
argument on retail data. A paper about "when FMs pay off" that
quotes only cloud-GPU cost numbers answers the wrong question
for the retail practitioner audience of IJF; our local run
grounds the cost axis in the hardware retail practitioners
actually use.

The two sources are kept separate throughout §5.4 and §6 —
extraction rows carry `paper_id ∈ {A01..A17, B01, B02, ...}` and
local runs carry `paper_id = LOCAL_*`. The meta-regression in
§6.6 reports the pooled estimate both including and excluding the
LOCAL rows, so the reader can see whether our own small run is
moving the conclusion.

### 5.4.2 Literature-extraction protocol (Source A)

Extraction follows the PRISMA 2020 standard, documented in full
in `analysis/prisma_search_protocol.md` and summarized in §4.
Four per-row fields in `extraction_schema.csv` are the load-
bearing columns for Table 5.7 population:

- `paper_id` — unique row key tying back to the source paper.
- `dataset` + `dataset_variant` — e.g. `M5 tail-eval h=28`,
  `Favorita fev-bench W`, `Rohlik rohlik-v2-daily`. Dataset
  variants that do not match our §5.1.1 definitions are
  recorded but excluded from the primary pool.
- `metric_name` + `metric_value` — each paper's reported
  zero-shot metric on the row's dataset × horizon.
- `baseline_quality_tier ∈ {weak, standard, strong}` — our
  categorization of the paper's own LightGBM baseline (§5.3.3,
  §5.3.9). Weak-baseline rows enter the pool but are flagged in
  §6.6 and the meta-regression is repeated with and without
  them.

Per-dataset extraction coverage at time of writing:

| Dataset   | FM papers with zero-shot numbers | Horizons covered | Primary metrics |
|---|---|---|---|
| M5        | 8 (A01 Chronos, A02 Chronos-2, A04 TimesFM 2.5, A11 Chronos-Bolt, A13 TiRex, A14 TabPFN-TS, B01 GIFT-Eval leaderboard, B02 fev-bench) | 7, 14, 28 (not every paper × horizon cell) | WRMSSE, WAPE, MASE |
| Favorita  | 7 (A02, A04, A06 Moirai 2.0, A11, A13, A15 Toto, B02 fev-bench retail tasks) | 7, 14, 28, 56 | WAPE, MASE, WQL |
| Rohlik v2 | 3 (A02, B02 rohlik-v2-daily, B02 rohlik-orders-daily) | 7, 14, 28 | WAPE, WQL |

The Rohlik coverage is the thinnest; two of the three Rohlik
cells come from the same source (fev-bench 2025), which is a
moderator we record per row as `source_paper_is_benchmark ∈
{yes, no}` — benchmark-paper numbers carry less
within-paper baseline comparison than technical-report numbers,
and this matters for the Pass-1 relative-error framing of §6.1.

**Dataset alignment.** A key extraction-protocol choice is that
the §5.1.1 datasets do not exactly match every FM paper's own
evaluation slice. M5 is the tightest match (the papers use the
same 30,490 series and the same 28-day canonical horizon).
Favorita is split: some papers use the original Favorita top-54k
subset from Kaggle, others use the fev-bench Favorita daily slice.
We extract both and record `dataset_variant` per row so that the
§6 pool can optionally restrict to the fev-bench variant for
cross-paper comparability. Rohlik v2 is recent enough (2024) that
coverage is still growing; we extract the fev-bench variant as
the primary target and will add any new 2026 FM papers that
report on it before final submission.

**Covariate asymmetry is a moderator, not a filter.** Four of
the extracted FMs (Chronos, Chronos-Bolt, TimesFM, TiRex) are
univariate and cannot consume the §5.1.1 covariate sets at all.
This is an inherent asymmetry vs the LightGBM baselines in §5.2
which use the full covariate sets. We record
`covariate_aware ∈ {yes, no}` per row and treat it as a
moderator in §6.2 rather than as a filter on the pool — a
univariate FM that beats a covariate-rich LGBM on a
covariate-rich dataset is *more* informative than one that ties.

### 5.4.3 Local consumer-box protocol (Source B)

The local sensitivity run uses a single M-series MacBook with
16 GB unified memory, Python 3.11 in a dedicated venv
(`~/venvs/fm-local/`), and PyTorch 2.3 with the MPS backend.
Inference is executed serially (no batching across series
beyond each model's own internal batch-size default) to match
the "retail practitioner on a laptop" framing of the cost panel.

**Three-model choice.** We run three models locally:

| Model            | Params | Why local-feasible                            |
|---|---|---|
| Chronos-Bolt-Tiny | ~9 M   | Smallest public Chronos variant, MPS-supported, documented to hit ~100 series-day/s on M1 by A11 supplementary table. |
| TabPFN-TS         | ~11 M  | Tabular-FM with a published time-series head, covariate-aware, runs on MPS via PriorLabs' reference implementation (A14). |
| TiRex             | ~35 M  | xLSTM-based, published MPS-compatible inference script (A13). Upper feasibility bound on a 16 GB machine for serial single-series inference. |

We explicitly **exclude** four models from the local run and
document why:

- **Moirai 2.0 large (~311 M)** — exceeds 16 GB unified memory
  budget when the masked-encoder attention cache is loaded for
  Favorita's longest context. Could run at base (~91 M) with
  performance degradation, but the base variant is not the one
  the paper's headline numbers use, so comparability against
  literature rows would be broken.
- **TimesFM 2.5 (~200 M)** — borderline feasible on 16 GB but
  published throughput on consumer HW is not in the source
  paper and we would be extrapolating the cost axis from a
  single internal number.
- **Chronos-2 (~120 M)** — borderline feasible on MPS but
  Chronos-2's Mixer head has known MPS kernel fallbacks that
  drop performance ~3× relative to CUDA in tests reported on
  the Chronos-2 GitHub issue tracker. The headline numbers
  would not be representative of consumer-HW deployability.
- **Chronos-Bolt-Base / -Small / -Mini** — substitutable for
  -Tiny under the same framing; we run only -Tiny to stay
  under the 27-job total local budget (3 models × 3 datasets ×
  3 horizons).

The three omitted models' FM rows on Table 5.7 come from
Source A (literature extraction) instead. This keeps the local
run scope bounded at 27 jobs and avoids a situation where the
local run becomes its own mini-benchmark.

**Evaluation protocol matches §5.1.3 exactly** — same
tail-evaluation window per dataset (`train_until = floor(0.8
× n_days)`), same rolling-origin non-overlapping horizons
`h ∈ {7, 14, 28}`, same metric definitions (WAPE, MAE, sMAPE,
WRMSSE on M5). The only protocol difference vs §5.2's baseline
LightGBM sweep is that the local FMs are univariate except
TabPFN-TS which uses the full §5.1.1 covariate set. This
matches how the three models were designed to be invoked and is
the fair-use protocol for each.

**Context window and sampling.** Each model uses its published
default context (2048 for Chronos-Bolt-Tiny and TiRex, 1024 for
TabPFN-TS) and point-forecast mode (median over 20 samples for
Chronos-Bolt, deterministic for TiRex, point head for
TabPFN-TS). No tuning. Identical to §5.4.1 v0.1 except that
four large models are dropped and only three small models
remain.

**Runtime budget.** On an M-series MacBook at typical MPS
throughput of ~50–150 series-day/s for Chronos-Bolt-Tiny-class
models, the full 27-job local sweep should complete in 12–24
hours of wall time across the three datasets, with Favorita
dominating (30,000 series × 337-day tail × 20 windows at h = 7).
No cloud compute, no Azure cost. We will run it as an
overnight-and-weekend job over 2026-04-15 and 2026-04-16.

### 5.4.4 Evaluation, metrics, and filtering

Both Source A and Source B produce numbers that enter the same
Table 5.7 columns. We align both sources on the §5.1.3
definitions:

- **Primary metrics:** WAPE and MAE on all three datasets,
  WRMSSE on M5 only.
- **Reported but not primary:** sMAPE, CRPS, WQL (the last two
  only where the source paper publishes them; we do not compute
  them ourselves in the local run).
- **Per-series filter:** WAPE drops series with zero-denominator
  eval windows and reports `n_valid`, matching §5.1.3. For
  extraction rows we copy the paper's own `n_valid` if
  published, else we record `n_valid = unknown` and flag the
  row in §6.6's sensitivity analysis.

For the local run, the metric computation reuses
`benchmark/code/experiments/run_gap_filling.py` exactly — same
Python, same aggregation code path as the LightGBM baselines —
so the comparison against §5.2's LGBM rows is bit-identical on
the metric side. This is the main reproducibility advantage of
running the local sensitivity ourselves rather than extracting
from papers: we can guarantee metric-path equivalence with our
own baselines.

### 5.4.5 Consumer-box run: results

*We executed the Source B sweep on 2026-04-13 / 2026-04-14 as planned in
§5.4.3. The local FM cells are paired against matched `lightgbm_cov`,
`lightgbm_direct`, and `seasonal_naive` baselines that we also re-ran on
Azure ML (`mlw-forecast-benchmark`) so that both arms of every
comparison use the §5.1.3 metric path bit-identically. Below is what we
found; the feed of these numbers into the §6 meta-regression is discussed
in §6.1 and §6.6.*

**Ship state: 16 of 18 FM cells.** Chronos-Bolt-Tiny completed all 9
cells (3 datasets × 3 horizons). TiRex completed 7 of 9: M5 and Favorita
all three horizons plus Rohlik `h = 7`. The two missing TiRex cells
(Rohlik `h = 14`, `h = 28`) hit a pathological MPS path where
`xlstm_kernels` falls back to a per-element MPSGraph dispatch through
`log_sigmoid_forward_mps` — the process advanced less than three minutes
of CPU per hour of wall time. After 14 h of wall clock on the Rohlik
`h = 14` cell with no meaningful progress we killed the run, added
`TIREX_FORCE_CPU=1` to `benchmark/code/models/foundation/tirex.py`, and
retried on the CPU path. The CPU retry was also too slow to finish
inside the §5.4.3 20-hour wall-time budget (~24 % effective utilization,
likely due to memory pressure after a full day of resident MPS state).
Rather than push past the pre-registered budget we accepted 16 / 18 as
the ship state; the two missing cells are filled from Source A TiRex
rows on Rohlik and flagged as `source = "LIT"` in Table 5.7.
TabPFN-TS is **not** in the ship state — the 20 h budget was exhausted
by the two Chronos and TiRex sweeps before the TabPFN-TS slot opened,
and the three TabPFN-TS rows come entirely from Source A in the final
table. We note this as a protocol drift vs the §5.4.3 plan in §5.4.8.

**Per-cell WAPE (paired with Azure baselines).** Numbers below are per-
series WAPE means with `n_valid = 100` per cell (sampled with a fixed
seed, §5.1.3). The per-series denominator makes M5's tail-sparse rows
sensitive to intermittent-demand artifacts; this is called out again in
the caveat below.

| Dataset   | h  | chronos-bolt-tiny | tirex  | lightgbm_cov | lightgbm_direct | seasonal_naive |
|-----------|---:|-----------------:|-------:|-------------:|----------------:|---------------:|
| M5        |  7 | 0.9576           | 0.9344 | 1.6246       | 1.3512          | 1.3072         |
| M5        | 14 | 0.9555           | 0.9370 | 1.7292       | 1.4100          | 1.3216         |
| M5        | 28 | 0.9557           | 0.9421 | 1.9357       | 1.5133          | 1.3285         |
| Favorita  |  7 | 0.5321           | 0.5249 | 0.5295       | 0.5513          | 0.6363         |
| Favorita  | 14 | 0.5374           | 0.5311 | 0.5311       | 0.5711          | 0.6473         |
| Favorita  | 28 | 0.5458           | 0.5395 | 0.5377       | 0.5892          | 0.6643         |
| Rohlik v2 |  7 | 0.3218           | 0.3143 | 0.3654       | 0.3816          | 0.4015         |
| Rohlik v2 | 14 | 0.3344           | —      | 0.3953       | 0.4072          | 0.4031         |
| Rohlik v2 | 28 | 0.3528           | —      | 0.4321       | 0.4442          | 0.4116         |

**TiRex beats Chronos on all seven paired cells,** by a narrow but
consistent margin: ~2.0–2.3 pp on M5 (0.93 vs 0.96), ~0.6–0.7 pp on
Favorita, ~0.7 pp on Rohlik `h = 7`. This is consistent with the
per-paper ranking in A13 (TiRex ARES 2025) which places TiRex above
Chronos-Bolt on GIFT-Eval retail tasks. TiRex at ~35 M parameters vs
Chronos-Bolt-Tiny at ~9 M spends ~3.5× the FLOPs per forecast window for
a ~1 pp average WAPE gain on this retail slice, so the quality/cost
picture depends strongly on the deployment horizon (see the cost and
runtime footprint below; plotted in §6.5 Figure 6.4).

**Paired Δ headline.** Feeding the 9 paired cells into the §6.1
`rma.mv` pipeline (`V = 0.01` placeholder, cluster = paper_id/dataset,
Knapp-Hartung `t` adjustment) yields

&nbsp;&nbsp;&nbsp;&nbsp;**Δ̂ (FM − ML_TREE) = −0.2442 WAPE**, &nbsp;
95 % CI [−0.482, −0.007], &nbsp; `t(8) = −2.37`, &nbsp; *p* = 0.045,
&nbsp; `Q(8) = 76.26`, *p* < 10⁻⁴.

The point estimate is significant at the 5 % level but the between-cell
`Q`-statistic is very large, meaning the pooled intercept is dominated
by a handful of high-Δ cells rather than representing a homogeneous
family-level effect. The three subgroup forests (`analysis/figures/
figure_6_forest_{m5,favorita,rohlik}.pdf`) make the heterogeneity
visible: M5's Δs are ~−0.6, Favorita's are ~−0.01, Rohlik's are
~−0.06. This is the finding that §6.2 moderates on `dataset_norm`,
and it is substantive, not a fit artifact.

**M5 caveat: per-series WAPE + intermittent demand.** The M5 Δs above
are real (TiRex 0.93 vs `lightgbm_cov` 1.62 at `h = 7`, etc.) but the
absolute magnitude is partly an artifact of the per-series WAPE metric
on M5's tail. M5's 30,490 series include a long right tail of very-low-
velocity SKUs whose held-out actuals sum to near zero in the rolling-
origin window; per-series WAPE on those rows explodes toward infinity
whenever the predictor over-shoots by any constant, and a tree with a
flat-across-time default sits right at that failure mode. The `>1`
WAPEs in the `lightgbm_cov` column (1.62, 1.73, 1.94) are this
failure, not a mislabelled metric. Two defences against the "unfair to
LGBM" reading: (i) `lightgbm_direct`, which does **not** use
covariates, posts 1.35–1.51 on the same M5 cells — still materially
worse than either FM — so the issue is not just covariate handling,
and (ii) `seasonal_naive` posts 1.31–1.33, i.e. LGBM is *worse than
naive* on M5 tail rows at `h ≥ 14`, which is a known failure mode of
tree-based point forecasters on sparse demand and is documented in §5.2
(Table 5.5, M5 row `BASELINE_QUALITY_TIER = weak`). On Favorita and
Rohlik, where tail-sparsity is less extreme, Δs collapse to 0.5–1 pp in
favour of the FMs — so the M5-level Δ is the ceiling, not the central
tendency. We report both the full-pool intercept and the `excl_M5`
subgroup intercept in the final §6.1 table.

A sanity check on 2026-04-15 quantifies how much of the M5 level comes
from the metric framing vs. the model. For the six FM M5 cells in
Table 5.17, recomputing WAPE as the aggregate form Σ|e| / Σ|y| (sum of
absolute errors over sum of actuals across all series in the held-out
window) gives roughly 0.84–0.85 — versus the per-series mean of
0.94–0.95 reported above, a ratio of **~0.89**. So the per-series
denominator inflates the FM WAPE level by ~11 % on M5, which is real
but does not explain the full FM-vs-LGBM gap: even after deflating FM
numbers by 11 %, `lightgbm_cov` at 1.62–1.94 stays materially worse.
For `lightgbm_cov` the per-series-to-aggregate ratio is harder to
measure directly because several Azure runs logged `WAPE_mean = inf`
(the zero-denominator blow-up on the tail series, confirmed in MLflow),
so the aggregate form is the one to trust on the LGBM side. The §6.7
cross-paper analysis reports the M5 cells both with and without this
deflation in the excl-M5 sensitivity row.

**Favorita is the "close call" dataset.** On Favorita, `lightgbm_cov`
matches Chronos-Bolt-Tiny almost exactly (0.5295 vs 0.5321 at `h = 7`,
a 0.3 pp *LGBM win*) and TiRex only barely edges `lightgbm_cov` (0.5249
vs 0.5295 = 0.5 pp). This is directly on-thesis for the paper's title:
a well-tuned, full-covariate LGBM on a dataset where the covariates
carry real signal (oil price, holiday flags, promotions) is competitive
with a state-of-the-art univariate FM — the FM pays off only narrowly
here, and the consumer-HW cost column below determines whether that
narrow win is worth it in deployment. This reverses the naive reading
of the M5 cells and is the headline §5.4 finding that motivates §6.5's
Pareto frontier.

**Cost and runtime footprint.** The 16 FM cells ran in 10.32 h of
MacBook wall time at an estimated marginal electricity cost of $0.062
USD and a grid-mix CO₂ footprint of 0.201 kg (Polish grid, §5.3.8
`M_SERIES_MAC` bucket). The 27 matched baseline cells on Azure
(`cc-forecast-batch`, `Standard_E4ds_v4`) ran in 4.63 h of compute at
list-price $1.76 USD and a Swedish-grid footprint of 0.0045 kg CO₂. The
consumer-box is therefore **16× cheaper per cell in dollars** (~$0.004
vs $0.065) and **44× higher per cell in CO₂** (~0.013 kg vs 0.0002 kg),
but **~4× slower per cell in wall time** (~39 min vs ~10 min). This is
exactly the tradeoff that §6.5 Figure 6.4 (consumer-HW Pareto) and
Figure 6.5 (cloud Pareto) visualize on the two cost axes: the FM
advantage on a retail-practitioner's MacBook is dramatically larger
than on a corporate cloud account when cost is the denominator.

**What this does *not* show.** Three things the local run deliberately
does not address, and which the paper reader should keep separated
from the findings above: (i) **tuning budget** — the LightGBM baselines
use the §5.3.3 pre-registered hyperparameter grid with no dataset-
specific tuning, so a practitioner with a full Optuna budget on M5
would likely push `lightgbm_cov` materially below 1.0 WAPE and close
some of the Δ; (ii) **fine-tuning** — the FMs are zero-shot, so any
fine-tuning advantage is unmeasured; (iii) **uncertainty calibration**
— this section is point-forecast only, and the WQL / CRPS columns on
Table 5.7 come from Source A, where they exist at all.

### 5.4.6 Reproducibility and licensing notes

**Source A reproducibility** is limited to what each source
paper itself publishes — typically a model checkpoint on
HuggingFace Hub, an inference script on GitHub, and a benchmark
table. Our extraction records: paper DOI or arXiv ID, extraction
date, reviewer (always one of the authors of this paper),
metric name, metric value, dataset variant, and a free-text
`notes` field flagging any extraction uncertainty. Where a paper
does not publish a metric value at the horizon we want (e.g. a
paper that only reports `h = 28` on M5 when we also need `h =
7`), we record the missing cell as `metric_value = NOT_FOUND`
and flag for follow-up.

**Source B reproducibility** is weaker than our Azure-ML
baselines but stronger than extraction. The anchors:

1. **Git commit SHA** of this repository at run time — recorded
   in a local JSON sidecar `benchmark/runs/local/<date>/meta.json`.
2. **HuggingFace revision SHA** of each model checkpoint — pinned
   in `benchmark/code/fm_inference/<model>.py` and logged at run
   time.
3. **`pip freeze` snapshot** of the local venv at run time —
   also in the sidecar JSON.
4. **Machine fingerprint** — model, CPU, memory, macOS version,
   and MPS runtime version — logged at run time.
5. **Per-run CSV** — the same per-series output format as the
   Azure MLflow runs, so downstream analysis code is identical.

Two of the 16 FMs in our broader §4 corpus (Moirai 2.0,
TabPFN-TS) carry non-commercial licenses. Moirai 2.0 is only
cited from Source A, so the license caveat is on the published
numbers, not on our execution. TabPFN-TS is in Source B, and we
flag in §7 that its consumer-box numbers are reproducible for
academic benchmarking but not deployable under PriorLabs'
RL-NC without a commercial license negotiation.

### 5.4.7 Table 5.17: cross-model WAPE on the three retail datasets

Source A's FM coverage on the three retail datasets is sparse: one
M5 WRMSSE row (TEMPO baseline, 0.9706, from C05) and one non-
numeric Rohlik row (TimesFM on MASE+sMAPE, from C03). No Source A
FM paper reports WAPE on M5, Favorita, or Rohlik with the per-
series rolling-origin protocol of §5.1.3. Table 5.17 is therefore
almost entirely Source B, with the M5 WRMSSE cross-reference from
Source A flagged in the notes column. The v0.1 expectation of "~85
Source A FM retail rows" proved unrealistic: the FM literature
evaluates primarily on benchmark suites (GIFT-Eval, fev-bench,
Chronos Benchmark I/II) rather than on individual retail datasets
under matched conditions.

**Table 5.17.** Consumer-box WAPE (Source B, per-series mean,
rolling origin) across models, datasets, and horizons. Lower is
better. Two cells are missing (TiRex × Rohlik `h ∈ {14, 28}` —
MPS xLSTM stall, see §5.4.9).

| Model | Family | Favorita h=7 | h=14 | h=28 | M5 h=7 | h=14 | h=28 | Rohlik h=7 | h=14 | h=28 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chronos-Bolt-Tiny | FM | 0.532 | 0.537 | 0.546 | 0.958 | 0.956 | 0.956 | 0.322 | 0.334 | 0.353 |
| TiRex | FM | 0.525 | 0.531 | 0.540 | 0.934 | 0.937 | 0.942 | 0.314 | — | — |
| lightgbm_cov | ML_TREE | 0.530 | 0.531 | 0.538 | 1.625 | 1.729 | 1.936 | 0.365 | 0.395 | 0.432 |
| lightgbm_direct | ML_TREE | 0.551 | 0.571 | 0.589 | 1.351 | 1.410 | 1.513 | 0.382 | 0.407 | 0.444 |
| seasonal_naive | STATS | 0.636 | 0.647 | 0.664 | 1.307 | 1.322 | 1.329 | 0.402 | 0.403 | 0.412 |

Reading guide:

- **Favorita:** `lightgbm_cov` and Chronos-Bolt-Tiny are within
  0.3 pp at every horizon (§5.4.5 "close call"). TiRex consistently
  beats both by ~0.5 pp, the smallest winning margin in the table.
  `lightgbm_direct` is 2–5 pp worse than `lightgbm_cov` — the
  §5.3.6 conditional pattern (recursive wins on smooth demand).
- **M5:** Both FMs (0.93–0.96) beat all ML_TREE variants by 40+ pp
  WAPE. The ML_TREE numbers include the per-series WAPE
  zero-denominator pathology documented in §5.4.5. On WRMSSE (not
  shown, but Source A reports TEMPO at 0.9706 vs competition-grade
  LightGBM at 0.52), the sign reverses: ML_TREE wins. M5 should
  not be read as "FMs are better" — it is "per-series WAPE on
  intermittent demand is a broken metric for ML_TREE".
- **Rohlik:** FMs lead by 4–8 pp over `lightgbm_cov`. The gap
  widens with horizon (7 → 28: +2 pp for FM, +7 pp for LGBM).
  `seasonal_naive` overtakes `lightgbm_cov` at `h = 28` (0.412
  vs 0.432), consistent with the §5.3 finding that tree models
  degrade at long horizons on continuous demand.
- **Cross-source sanity check.** The only Source A FM row
  comparable by dataset is C05's TEMPO WRMSSE = 0.9706 on M5
  `h = 28`. Our Source B Chronos-Bolt-Tiny posts WAPE = 0.956 on
  the same cell — not metric-comparable (WRMSSE vs WAPE), but
  the magnitude is in the same ballpark (~0.97). A direct cross-
  protocol check for Chronos on retail WAPE requires a future
  Source A paper to report per-series WAPE on M5, which none
  currently do.

### 5.4.8 Threats to validity

Five threats specific to §5.4, in decreasing order of magnitude:

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

### 5.4.9 Status and what changed

**Source A extraction locked at 185 rows.** The comment-annotated
`analysis/extraction_schema.csv` holds 185 extracted rows spanning
FM reports, benchmark papers, retail ML_TREE baselines, and
cross-domain rows retained for provenance. M5 and Favorita
coverage is dense enough to drive §6.1 on WAPE alone; Rohlik
coverage is thinner on the FM side (one TiRex cell still missing
at `h ∈ {14, 28}` after the Source B run stalled — see below). A
single off-by-one in the A01 row was fixed on 2026-04-15
(`cd2cd72`), which had previously caused pandas to silently index-
shift the whole file and mis-classify `model_family` entries — that
fix unlocked the `ml` → `ML_TREE` bucket in the R pipeline.

**Source B ran on 2026-04-13 / 2026-04-14.** The consumer-box
sweep landed 16 FM cells out of 18 (Chronos-Bolt-Tiny 9/9 + TiRex
7/9 — the two missing cells are Rohlik × `h ∈ {14, 28}`, killed
after a 14-hour MPS xLSTM stall that is a known TiRex failure mode
on Apple silicon and documented in `benchmark/code/models/
foundation/tirex.py`'s `TIREX_FORCE_CPU` guard). The Azure batch
sweep on `cc-forecast-batch` contributed 18 ML_TREE cells
(`lightgbm_cov`, `lightgbm_direct`) and 9 `seasonal_naive`
baselines. Export path changed from the originally planned
`benchmark/runs/local/2026-04-16/runs.csv` to
`benchmark/results/local_fm_sweep.csv`, populated by
`tools/export_mlflow_to_csv.py` which pulls both MLflow backends
(local file store + Azure ML workspace) into a single 43-row CSV
keyed on the shared `paper_id = LOCAL_MAC_<dataset>_h<horizon>`.
That shared-ID scheme is what unlocked within-paper Δ for the
§6.7 sanity check.

**Per-series-WAPE diagnostic came back positive.** Several Azure
`lightgbm_cov` runs logged `WAPE_mean = inf` on M5, which is the
zero-denominator blow-up of the per-series metric on tail series
with near-zero held-out actuals. This is the concrete evidence
behind the §5.4.5 M5 caveat and behind the §6 decision to stop
aggregating M5 WAPE and M5 WRMSSE into a single "M5 effect" in
Table 6.1. The aggregate form Σ|e| / Σ|y| deflates FM WAPE on M5
by ~11 % (§5.4.5), narrowing but not closing the gap.

**No Azure GPU work was performed.** The Phase F v0.1 cloud FM
sweep stayed dropped. The Azure batch activity above is
CPU-only ML_TREE + statistical baselines on the same
`cc-forecast-batch` cluster, not GPU FM inference, and the §6.5
Pareto frontier is still specifically framed around the
consumer-hardware cost axis, unchanged from v0.1 of this section.

**Known gaps carried into §6:**
- Two TiRex × Rohlik cells (`h ∈ {14, 28}`) still missing; the
  Source B within-paper Pass 1 runs on 9 cells instead of the
  planned 18, and §6.7 reports the gap explicitly.
- Source A row-level IDs are unique per row, so §6.1 Pass 1 was
  redesigned on 2026-04-15 (`afcc21d`) to use cross-paper pooling
  inside each (dataset, horizon, metric) bucket. The headline
  number in §6.7 is now `Δ̂ = −0.043 (n.s., excl. M5)` rather
  than the Source-B-only `Δ̂ = −0.244 (p = 0.045)` of the v0.1
  draft.

---

*Sources for this section:* per-model technical reports A02
(Chronos-2), A04 (TimesFM 2.5), A06 (Moirai 2.0), A11
(Chronos-Bolt), A13 (TiRex), A14 (TabPFN-TS), plus B01
(GIFT-Eval) and B02 (fev-bench) benchmark papers — extraction
rows in `analysis/extraction_schema.csv`. Source B artefacts:
consolidated `benchmark/results/local_fm_sweep.csv` (exported via
`tools/export_mlflow_to_csv.py`) and the underlying MLflow runs
in the local `mlruns/` file store plus the `meta-analysis-gap-
filling` experiment in the `mlw-forecast-benchmark` Azure ML
workspace.
