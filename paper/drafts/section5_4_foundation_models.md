# §5.4 Foundation Model Protocol — DRAFT v0.1

*Drop-in draft for §5.4 of the paper (Gap-Filling Experiments —
Foundation Models). This section defines the zero-shot FM
protocol that will populate Table 5.7 (§5.2.4) once Phase F lands.
Results are blocked on Azure GPU quota approval
(`Standard_NC6s_v3` × 1 in `swedencentral`, quota requested
2026-04-13). The protocol is frozen now so the run is executable
as soon as the quota clears.*

---

### 5.4.1 Scope and choice of models

Phase F evaluates six public foundation models zero-shot on the
three retail datasets of §5.1.1 under the protocol of §5.1.3. The
six models were selected from the 16 candidate FM papers indexed
in the PRISMA screen (§4) by applying four inclusion rules:

1. **Model weights publicly downloadable** (HuggingFace Hub or
   equivalent) — excludes TimeGPT-1 (A07, closed API) and any
   paper that only reports zero-shot numbers without releasing
   the model.
2. **Inference script released by the authors** — so our
   "zero-shot" run uses the authors' own preprocessing, context
   window construction, and sampling defaults. This rules out a
   category of reproduction errors where a reviewer rewrites the
   loader and changes the score.
3. **Published retail or mixed-domain zero-shot benchmark** — at
   least one retail or retail-adjacent task in the paper's own
   evaluation, so our numbers are anchored to a comparable
   reference point. This excludes models that only report LSF
   (ETT / Weather / ECL) in their own papers.
4. **Covers the architectural variation space of §4** — at least
   one encoder-only (Chronos), one decoder-only (TimesFM), one
   masked-encoder (Moirai), one xLSTM-based (TiRex), one compact
   tabular-FM baseline (TabPFN-TS), and one instruction-tuned
   descendant (Chronos-2). This keeps the 6-model grid small
   enough to run on a single GPU node while spanning the five
   architectural families our taxonomy in §4 identifies.

The resulting list is:

| Model          | Paper ref | Size   | Context | Covariate-aware | License          |
|---|---|---|---|---|---|
| Chronos-Bolt (Base) | A11 (AWS 2024)        | ~200 M | 2048   | no (univariate)    | Apache-2.0       |
| Chronos-2           | A02 (arXiv 2025)      | ~120 M | 8192   | yes (Mixer head)   | Apache-2.0       |
| TimesFM 2.5         | A04 (Google 2025)     | ~200 M | 2048   | no (univariate)    | Apache-2.0       |
| Moirai 2.0 (large)  | A06 (Salesforce 2025) | ~311 M | 5000   | yes (masked enc.)  | CC-BY-NC-4.0 †   |
| TiRex               | A13 (ARES 2025)       | ~35 M  | 2048   | no (univariate)    | Apache-2.0       |
| TabPFN-TS           | A14 (PriorLabs 2025)  | ~11 M  | 1024   | yes (tabular)      | PriorLabs RL-NC ‡|

† *Moirai 2.0's non-commercial license is noted in §5.4.4 as a
reproducibility-but-not-deployability caveat.*
‡ *TabPFN-TS is non-commercial for research; cite-and-reproduce
is permitted. See §5.4.4.*

Two notable omissions from the grid deserve a sentence: **Toto**
(A15) was excluded because it does not publish a zero-shot retail
number in its own paper (only LSF) and its published inference
throughput on a single A10/V100 would push the 54-job sweep out of
our GPU budget; we flag this in §8.1. **Sundial** (A16) was
excluded for the same reason plus a context-length cap that would
force truncation on Favorita. Both models remain candidates for a
Phase G extension if GPU budget allows.

### 5.4.2 Compute and GPU cluster

Zero-shot inference runs on Azure ML compute cluster
`cc-forecast-gpu` (Standard_NC6s_v3, 1× NVIDIA V100 16 GB, 6 vCPU,
112 GB RAM, region `swedencentral`), inside Docker environment
`forecast-benchmark-gpu-env:2`. The environment is identical to
`forecast-benchmark-cpu-env:1` except for the CUDA base image
(`nvidia/cuda:12.1.1-cudnn8-runtime`) and the addition of
`torch==2.3.0+cu121`, `transformers==4.41`, `accelerate==0.30`,
`chronos-forecasting==1.4.0`, `timesfm==1.2.0`,
`uni2ts==1.1.0` (for Moirai 2.0), `tirex==0.3.1`, and
`tabpfn-time-series==0.2.0`.

Quota request: one NC6s_v3 node, 6 vCPU, 4 weeks, for Phase F +
Phase F buffer. Standard approval time in `swedencentral` is
24–72 hours per the Azure ML capacity page. Phase F is frozen
against the GPU cluster until quota clears; the CPU baselines
(§5.2–§5.3) are already complete and independent of Phase F.

Per-job cost is computed in-job from Azure's published per-second
pricing for `Standard_NC6s_v3` in `swedencentral` ($1.24/hr at
time of writing) and CO₂ uses the region's 2025 marginal
intensity (0.274 kgCO₂eq/kWh), matching §5.1.2 so the FM and
baseline cost envelopes in §6.3 are on the same footing.

### 5.4.3 Evaluation protocol

Phase F uses the **same rolling-origin non-overlapping tail
evaluation of §5.1.3** on the same three datasets, the same
train/eval split (`train_until = floor(0.8 × n_days)`), and the
same horizons `h ∈ {7, 14, 28}`. The five protocol choices that
differ from the baseline sweep — and all five are frozen in this
section — are:

1. **Context window per model.** Each model uses its published
   default context length (Table in §5.4.1). When the published
   default exceeds the tail-eval pre-window available (e.g.
   TimesFM 2.5 at context 2048 on an 281-day Rohlik tail, where
   the pre-window has 1,121 days — always sufficient), we use
   the full default. When the context exceeds the series length
   (never the case on our three datasets), we left-pad with
   zeros, which matches Chronos-Bolt and TimesFM 2.5 default
   behavior. Context length is recorded per-row in the Table 5.7
   output and is a moderator variable in the §6 meta-regression.

2. **Sampling / decoding.** All six models are evaluated in their
   **point-forecast mode** (median for Chronos/Chronos-2 at
   `num_samples = 20`; deterministic decoder output for TimesFM
   2.5 and TiRex; masked-encoder mean for Moirai 2.0;
   TabPFN-TS's published point-forecast head). We do not tune
   sampling parameters. We also do not report probabilistic
   metrics (CRPS, WQL) in §5.4 to keep the comparison aligned
   with §5.2's WAPE / MAE / WRMSSE grid; probabilistic metrics
   are tabulated separately in Appendix C for the subset of
   models that publish them.

3. **Covariate handling.** Four of the six models are
   univariate (Chronos-Bolt, TimesFM 2.5, TiRex, and the
   covariate-free fallback of Chronos-2). For those four the
   §5.1.1 dataset covariates are unused in Phase F — the
   comparison against LightGBM on §5.2's covariate-rich protocol
   is therefore an inherent asymmetry and is flagged in §6.1 as
   a moderator variable. Chronos-2, Moirai 2.0, and TabPFN-TS
   are evaluated twice: once univariate (matching the other
   four) and once with the full §5.1.1 covariate set. This
   isolates the "covariate-aware FM" contribution from the
   "zero-shot FM base capability" contribution on the two
   axes that matter for retail.

4. **Per-series handling.** Each evaluation window is a
   length-`h` forecast produced by **a single FM forward pass**
   with the model's published context. The forecasts are
   gathered into a `series × h × n_windows` tensor by the same
   script used for the LightGBM recursive and direct variants,
   so the metric computation is bit-identical across model
   families.

5. **Per-metric filtering.** WAPE, MAE, sMAPE, and (on M5) WRMSSE
   are computed with the same per-series filters as §5.1.3:
   WAPE drops series with zero-denominator eval windows and
   reports `n_valid`; WRMSSE uses the full 12-level Makridakis
   hierarchy. This is critical for the FM comparison because
   any mismatch in filtering would produce a 5–15% accounting
   gap that would dominate the real FM-vs-LGBM signal.

### 5.4.4 Reproducibility and licensing notes

Phase F produces the same five reproducibility anchors as §5.1.5
(git commit, pipeline run name, data asset version, environment
version, MLflow run URL), plus two FM-specific additions:

1. **Model checkpoint SHA.** Each FM is pinned to a specific
   HuggingFace revision SHA, recorded as a parameter on the
   MLflow run. A future `main` update of a FM will not silently
   change our Phase F numbers.
2. **Inference script commit.** We use each author's published
   inference script at a pinned git SHA, cited in the per-row
   notes of Table 5.7. This gives reviewers an exact
   reproduction path even if the author's `main` branch moves.

Two models carry non-commercial licenses: **Moirai 2.0**
(CC-BY-NC-4.0) and **TabPFN-TS** (PriorLabs RL-NC). Both are
evaluable and reproducible for academic benchmarking but are not
deployable without a commercial license negotiation. §7
(Limitations) notes that this paper's "FM is competitive with
LightGBM on X" claims have a deployability caveat on two of the
six models, which matters for the retail practitioner audience.

### 5.4.5 Expected results grid

The full Phase F results will populate Table 5.7 in §5.2.4.
Skeleton dimensions and placeholder cost estimate:

- **Rows:** 6 FMs × 3 datasets × 3 horizons = 54 primary rows,
  plus 3 covariate-aware duplicates (Chronos-2, Moirai 2.0,
  TabPFN-TS) × 3 datasets × 3 horizons = 27 extra rows, for 81
  FM rows total. Seasonal Naive and the best-per-dataset LGBM
  row are duplicated from §5.2 for readability (another 6
  rows). Grand total: 87 rows.

- **Cost estimate.** Per-model inference throughput from the
  source papers (A11/A13/A14 for the small models, A02/A04/A06
  for the large) puts each model at 20–250 series-days/s on
  V100. The dominant cost is Favorita (30k series × 337-day
  eval window × 20 sliding origins per horizon ≈ 200 M
  series-day predictions per horizon per model). Summing the
  six models × three horizons × three datasets under each
  paper's published throughput gives a point estimate of
  **$18–24 for the full 54-job primary sweep** (confidence
  interval: $14–32 at the throughput extremes).

- **Runtime projection.** On a single NC6s_v3 node the full
  primary sweep should fit in ~18–26 wall-clock hours of
  continuous GPU. The covariate-aware extension runs another
  ~8 hours on top of that. This is comfortably inside Azure
  ML's 168-hour job limit and does not require distributed
  inference across multiple GPUs.

These numbers are placeholders until Phase F runs; §6.3 will
replace them with the actual numbers from the Table 5.7 fill-in.
The order-of-magnitude gap against the baseline sweep's $2.05 is
the load-bearing quantity for the Pareto analysis: if the six
FMs collectively cost ~$20 for a comparable accuracy grid, then
the cost-accuracy frontier of §6.3 has to ask whether any FM
clears *both* the accuracy bar (FM > best LGBM per dataset) *and*
the cost bar (FM cost comparable to or below LGBM direct cost on
the same dataset). On Rohlik and Favorita the cost bar is
already extremely low ($0.12 and $1.12 respectively for the
full 9-job baseline sweep), and the FM's cost is 15–200× that
per dataset. On M5 the gap narrows because the baseline is
already $0.81 and the direct-LightGBM variant is the winning
protocol. The Pareto picture is dataset-conditional and that
conditionality is the central finding of §6.3.

### 5.4.6 Threats to validity specific to §5.4

Four FM-specific threats to validity are worth flagging here so
§6 and §7 have a single place to cite:

1. **Zero-shot ≠ fair.** All six models are evaluated zero-shot
   with no fine-tuning, no task-specific calibration, and no
   quantile recalibration on the target distribution. A paper
   that tuned Chronos-2 on a few hundred Rohlik SKUs would
   almost certainly report better numbers than our zero-shot
   row. We report zero-shot because (a) it is the mode
   practitioners actually invoke FMs in, (b) the literature
   disagrees about what counts as "fine-tuning" in this setting,
   and (c) it keeps the compute budget tractable. Fine-tuned
   evaluation is explicit out of scope for this paper.

2. **Covariate asymmetry.** Four of the six FMs cannot consume
   the §5.1.1 covariate sets at all. The LightGBM baselines in
   §5.2 use the full covariate sets. This is an inherent
   asymmetry that biases the comparison toward LightGBM on
   covariate-driven datasets (M5: SNAP, prices, events;
   Favorita: oil, promotions, transactions) and is not
   correctable inside a zero-shot protocol. §6.1 treats
   covariate-aware vs univariate as a moderator variable.

3. **Context length vs dataset series length.** On the three
   datasets we use, the pre-window available to the FM (series
   length minus eval window minus forecast horizon) is always
   larger than each model's default context. So no truncation
   occurs, and the context-length column in Table 5.7 is the
   model's own choice, not our dataset's constraint. On
   shorter benchmarks like ETT this asymmetry flips and is
   worth flagging.

4. **Top-30k Favorita cap propagates to FM results.** Same cap,
   same selection rule, same velocity bias as §5.1.1. We flag
   this in §7 alongside the LGBM version of the same caveat.

### 5.4.7 Status

Phase F is **ready-to-run** pending GPU quota. All inference
scripts are downloaded and pinned to SHAs in the repository at
`benchmark/code/fm_inference/{model}.py`. The pipeline YAML
`benchmark/code/pipelines/fm_phase_f_consolidated.yaml` defines
the 81-job DAG and is the single-command trigger. Results will
appear in Table 5.7 of §5.2.4 and propagate into the §6
meta-regression.

---

*Sources for this section:* Per-model technical reports A02
(Chronos-2), A04 (TimesFM 2.5), A06 (Moirai 2.0), A11
(Chronos-Bolt), A13 (TiRex), A14 (TabPFN-TS) — extraction rows in
`analysis/extraction_schema.csv`. FM inference scripts at their
respective GitHub repositories, pinned SHAs recorded in
`benchmark/code/fm_inference/README.md` (to be committed with
Phase F artifacts).
