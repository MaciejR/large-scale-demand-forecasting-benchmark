# Forecast Meta-Analysis — Project Instructions

**Paper:** "When Do Foundation Models Pay Off for Retail Demand Forecasting? A Systematic Review and Cross-Benchmark Meta-Analysis"

**Target:** International Journal of Forecasting (IJF). arXiv preprint first. PRISMA 2020 systematic review format — the meta-analysis *is* the paper, not a benchmark.

## Current State (2026-04-14)

**Phases B–E complete.** Full 27-job LightGBM baseline grid across M5 / Rohlik v2 / Favorita top-30k is landed:
- M5: pipeline `mighty_morning_6qz5c4jmwm`, best LGBM = direct h=7 WRMSSE 0.5598
- Rohlik v2: pipeline `goofy_pear_g54m1skybs`, best LGBM = recursive h=7 WAPE 0.3654
- Favorita top-30k: pipeline `loyal_roti_bcc63n9gkh`, best LGBM = recursive h=7 WAPE 0.5295
- Total baseline sweep cost: **$2.049** across 27 jobs on `cc-forecast-batch` (E4DS_V4)
- Main cross-dataset finding: direct-vs-recursive gap inverts with intermittency (M5 direct wins, Rohlik/Favorita recursive wins, Favorita gap grows with horizon). See §5.3.6 + §5.3.8 (Table 5.8).

**Phase F pivoted (2026-04-14).** Azure GPU quota not available. Replaced with **1+3 hybrid**:
1. **Primary FM rows come from literature extraction**, not own runs. The 214-row `analysis/extraction_schema.csv` already covers zero-shot FM numbers on M5/Favorita/Rohlik from B01 (GIFT-Eval), B02 (fev-bench), A01/A02/A04/A06/A11 (Chronos/Chronos-2/TimesFM 2.5/Moirai 2.0/Chronos-Bolt). §6 is runnable today on this data.
2. **Own FM runs scoped to consumer-box sensitivity.** Limited local run on MacBook via PyTorch MPS, only for Chronos-Bolt-Tiny + TabPFN-TS + TiRex on the three datasets. Purpose: anchor Figure 6.5 consumer-CPU Pareto panel (the F04 replication branch), not fill Table 5.7. This matches the IJF framing "cost for retail practitioner with a laptop" better than V100 numbers would.

## Paper Drafts (`paper/drafts/`)

| File | Status | Purpose |
|---|---|---|
| `section5_1_experimental_setup.md` | draft v0.1 (203 L) | Shared protocol, Table 5.1 datasets, §5.1.3 eval, §5.1.4 model families |
| `section5_2_results.md` | draft v0.1 (146 L) | Table 5.2 cross-dataset summary, Table 5.6 cost envelope, Table 5.7 FM placeholder |
| `section5_baseline_reliability.md` | draft v0.2 (524 L) | §5.3 cross-dataset analysis. Table 5.3 M5, 5.4 Rohlik, 5.5 Favorita, 5.8 direction-gap synthesis |
| `section5_4_foundation_models.md` | draft v0.1 (277 L) | FM protocol. **Needs rewrite to 1+3 framing** — currently assumes Phase F on V100 |
| `section6_meta_regression.md` | draft v0.1 (342 L) | Pooling strategy, 8 moderators, H1–H4 pre-registered, Pareto (§6.5 consumer-CPU panel is now primary, not sensitivity) |

## Environment & Compute

- **Azure ML workspace:** `mlw-forecast-benchmark` (RG `rg-forecast-benchmark`, `swedencentral`)
- **CPU compute (active):** `cc-forecast-batch` — E4DS_V4, 4 vCPU / 32 GB, 0–4 nodes, $0.38/hr
- **CPU dev:** `ci-forecast-dev` — E4DS_V4 single
- **GPU compute:** none available. Do NOT plan work that requires it.
- **Environment:** `forecast-benchmark-cpu-env:1` (Python 3.11, `lightgbm==4.6.0`, `pandas==2.2.0`, `numpy<2`)
- **CO₂ intensity:** 0.274 kgCO₂eq/kWh (swedencentral 2025 baseline)
- **Data assets:** `azureml:m5-sales:1`, `azureml:rohlik-train-v2:1`, `azureml:favorita-train:1`

## Local Consumer-Box FM Run (new workstream)

For the 1+3 hybrid Figure 6.5 anchor:
- **Host:** MacBook (M-series), Python 3.11 in a local venv, not Azure
- **Framework:** PyTorch with MPS backend (not CUDA)
- **Models in scope:** Chronos-Bolt-Tiny (A11), TabPFN-TS (A14), TiRex (A13). Skip Moirai 2.0 (311 M params, risky on 16 GB unified memory), skip Chronos-2 (120 M, borderline), skip TimesFM 2.5 (200 M, borderline).
- **Datasets:** M5 (30,490 series), Rohlik v2 (5,390 series), Favorita top-30k. Same eval windows as §5.1.3.
- **Why:** F04 (arXiv 2602.10848) already publishes consumer-box throughput numbers for Chronos-Bolt on energy load. Our runs replicate that argument on retail.
- **Output:** CSV rows injected into `extraction_schema.csv` with `paper_id = LOCAL_*`, plus MLflow-equivalent JSON sidecar for reproducibility (local MLflow tracking server, not Azure).
- **Not in scope:** HF-Hub revision pinning + published-model reproducibility anchors are still required, but we run on local-machine-version-pinned PyTorch, not Azure docker. Limitation flagged in §5.4 / §7.

## Reproducibility Anchors

Every baseline result in §5.2–§5.3 is tied to:
- Git commit SHA (MLflow parameter)
- Azure ML pipeline run name (`mighty_*`, `goofy_*`, `loyal_*` for Phases C/D/E)
- Registered data asset version (immutable `:1` suffix)
- Environment version (`forecast-benchmark-cpu-env:1`)

Local FM runs use a weaker equivalent: git SHA + HuggingFace revision SHA + `pip freeze` snapshot. Documented in §5.4 as a reproducibility-but-not-deployability caveat.

## Working Notes

- Tables 5.6 (cost envelope, §5.2.3) and 5.8 (direction-gap synthesis, §5.3.6) do *not* overlap — the renumbering from 5.6→5.8 in §5.3 was deliberate to resolve the conflict with §5.2.3.
- §5.3 has been deduped against §5.1/§5.2. Do not re-introduce the 3-variant description in §5.3 intro — it belongs in §5.1.4.
- Tweedie sMAPE bias (LGBM ≈ 2–2.5× worse than SN on sMAPE across all three datasets) is a **universal retail finding**, not an intermittent-specific artefact. Referenced from §5.3.5 and §5.3.9.
- Training-budget artefact: direct LGBM's horizon-growth penalty on Favorita is budget-bound (fixed 300 trees per head), not protocol-intrinsic. Flag in §5.3.5/§5.3.7 point 4 and §6 moderator table.
- C12 (arXiv 2512.00888) is about **tabular FMs (TabPFN/TabICL)**, not TS FMs. Cite only as cross-domain analogue, never as direct TS FM hardware evidence. Protocol file and extraction schema already flag this — do not revert.

## Todo Queue (after the 1+3 pivot)

1. **§5.4 rewrite** — re-scope from "Phase F on V100 GPU" to "extraction-anchored + local consumer-box sensitivity"
2. **§5.4.8 local run methodology** — new subsection for MPS inference protocol on the three small FMs
3. **§6.5 reframe** — consumer-CPU Pareto panel is now **primary**, GPU-cloud Pareto is sensitivity (if it appears at all)
4. **Run local FM inference** — three models × three datasets × three horizons = 27 local-run rows
5. **Optional Phase F extension** — direct-LGBM with horizon-scaled tree budget on Favorita (CPU, cheap), to test the training-budget artefact hypothesis from §5.3.5
6. **§6 R code** — `analysis/meta_regression.R` with mixed-effects REML, forest plots, Pareto figures. Can run today on extraction alone.

## What NOT to Do

- Do not plan anything that requires Azure GPU quota. It's not coming.
- Do not run full Favorita on E4DS_V4 without `--max-series 30000` — the 125 M-row dataset OOMs on 32 GB.
- Do not cite C12 as TS FM evidence (tabular-FM paper, tagged in protocol file).
- Do not remove the training-budget-artefact caveat from §5.3.5/§5.3.7/§6 — it's load-bearing for the direct-vs-recursive claim honesty.
- Do not re-duplicate protocol description in §5.3 intro. §5.1.4 is the single source.
- Do not report sMAPE as a primary metric. WAPE + MAE + WRMSSE only. sMAPE only for reproducibility with literature, always flagged as unreliable on retail.
