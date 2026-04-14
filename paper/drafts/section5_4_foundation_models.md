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

### 5.4.5 Reproducibility and licensing notes

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

### 5.4.6 Populating Table 5.7

The populated Table 5.7 comes from the union of Source A and
Source B. For every (model, dataset, horizon) cell, we prefer
Source A if the source paper's protocol matches §5.1.3 closely
enough (benchmark-paper rows from B01 and B02 typically match),
and we use Source B only for the three LOCAL models that are
also covered by Source A (Chronos-Bolt, TiRex, TabPFN-TS). This
produces a natural sanity check: our LOCAL row and the paper's
published row should be within a small percentage on the same
(dataset, horizon, metric) cell. If they diverge by more than
~5%, the divergence is itself a finding and is reported as a
cross-protocol gap in the row's `notes` field.

**Table 5.7 [placeholder — source split].** Foundation model
zero-shot results across the three datasets × three horizons,
with source provenance column. Eleven FM rows per (dataset,
horizon) cell = ~99 rows total; we expect ~85 of those to be
populated from Source A and 27 from Source B (with the three
models in Source B creating a 3 × 9 = 27-row overlap used as
the cross-protocol sanity check above).

The columns of Table 5.7 in the final draft will be:
`Model | Source (A/B) | Dataset | h | Context | WAPE | MAE |
WRMSSE (M5) | Runtime | Cost | Notes`. Cost is populated from
Source A's reported per-series inference time (if any) × the
appropriate price class (§6.5), or from our own wall-clock
measurement on the local MacBook for Source B rows.

### 5.4.7 Threats to validity

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
   this drift, and §5.4.6 treats >5% gaps as findings.

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

### 5.4.8 Status and next steps

**Source A (extraction) is ready today.** The 214-row
`extraction_schema.csv` already covers the majority of the FM
cells for M5 and Favorita; Rohlik coverage is thinner but
sufficient for a preliminary forest plot. The §6 meta-regression
runs on Source A alone and does not block on Source B.

**Source B (local run) is scheduled for 2026-04-15 / 2026-04-16**
as an overnight-and-weekend job on the MacBook. Deliverable:
- 27 rows in `benchmark/runs/local/2026-04-16/runs.csv` using
  the §5.1.3 metric definitions
- Injected into `extraction_schema.csv` with `paper_id =
  LOCAL_{chronos_bolt_tiny,tabpfn_ts,tirex}`
- Per-run sidecar JSON with the five reproducibility anchors of
  §5.4.5
- A 3 × 9 cross-protocol comparison table in §5.4.6 against the
  corresponding Source A rows

**No Azure GPU work is planned.** The Phase F v0.1 cloud sweep is
explicitly dropped from the project todo queue. If GPU quota
becomes available later, Phase F may be revived as a second
sensitivity run — but the paper does not depend on it, and the
§6 Pareto frontier (§6.5) is specifically framed around the
consumer-hardware cost axis, so revival would add a second
sensitivity panel rather than change the main finding.

---

*Sources for this section:* per-model technical reports A02
(Chronos-2), A04 (TimesFM 2.5), A06 (Moirai 2.0), A11
(Chronos-Bolt), A13 (TiRex), A14 (TabPFN-TS), plus B01
(GIFT-Eval) and B02 (fev-bench) benchmark papers — extraction
rows in `analysis/extraction_schema.csv`. Local run artifacts
in `benchmark/runs/local/2026-04-16/` (to be committed after
the weekend run).
