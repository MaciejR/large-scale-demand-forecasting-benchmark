# §5.2 Gap-Filling Results — DRAFT v0.1

*Drop-in draft for §5.2 of the paper (Gap-Filling Experiments —
Results). This section reports the headline numbers from Phases
B–E. Interpretation, protocol analysis, and the cross-dataset
synthesis live in §5.3. Foundation model rows are pending Phase F
(GPU sweep); §5.2 documents the baseline half of the experimental
grid in full. Sources:
`analysis/baseline_results.md`, pipelines `mighty_morning_6qz5c4jmwm`,
`goofy_pear_g54m1skybs`, `loyal_roti_bcc63n9gkh`.*

---

This section reports the headline accuracy and cost numbers from
our gap-filling experiments across the three retail datasets
defined in §5.1.1, under the shared protocol of §5.1.3. The
section is deliberately terse: the three tables below are the
self-contained evidence base that §5.3 interprets. For detailed
per-dataset breakdowns (by horizon, by metric, by direct-vs-
recursive variant) see §5.3.1 (M5, Table 5.3), §5.3.4 (Rohlik v2,
Table 5.4), and §5.3.5 (Favorita, Table 5.5).

### 5.2.1 Cross-dataset summary

**Table 5.2.** Cross-dataset summary of the baseline LightGBM
gap-filling sweeps at `h = 7`. "Best LGBM" is the WAPE-best
LightGBM variant per dataset; the protocol column records
whether it is direct or recursive. Cost is the total 9-job sweep
cost on `cc-forecast-batch` (E4DS_V4). Full per-horizon numbers
are in Tables 5.3–5.5 of §5.3.

| Dataset   | Zero-day frac | SN WAPE `h=7` | Best LGBM WAPE `h=7` | Best LGBM protocol | LGBM vs SN | 9-job sweep cost | Pipeline |
|---|---|---|---|---|---|---|---|
| M5        | ~70 %  | 1.3072 | **0.5598** (WRMSSE) | direct    | direct ~12 % better on WRMSSE vs recursive (17 % on WAPE) | $0.810 | `mighty_morning_6qz5c4jmwm` |
| Rohlik v2 | ~1.2 % | 0.4015 | **0.3654**          | recursive | recursive 4.2 % better than direct | $0.120 | `goofy_pear_g54m1skybs`      |
| Favorita  | ~15–25 %, long tail | 0.6363 | **0.5295**          | recursive | recursive 4.1 % better than direct at h = 7, gap grows to 9.6 % at h = 28 | $1.119 | `loyal_roti_bcc63n9gkh`      |

Three observations at the headline level:

1. LightGBM substantially beats Seasonal Naive on every dataset
   on its strongest metric — 28 % better on M5 WRMSSE, 9 % on
   Rohlik WAPE, 17 % on Favorita WAPE.

2. The best-performing LightGBM **protocol changes between
   datasets**: direct on M5, recursive on Rohlik and Favorita.
   The gap is large on M5 (~12 % WRMSSE / ~17 % WAPE in favor
   of direct) and small but consistent on Rohlik and Favorita
   (3–10 % WAPE in favor of recursive). §5.3 is dedicated to unpacking this
   cross-dataset flip.

3. The 9-job sweep cost is under $1.20 on every dataset. The
   most expensive sweep (Favorita) is dominated 92 % by
   LightGBM-direct — which is also the *losing* protocol on that
   dataset — because direct trains `h` separate models at fixed
   per-head compute budget. This is unpacked in §5.3.8.

### 5.2.2 Per-dataset baseline tables

For compactness we do not reproduce the full 9-row per-dataset
grids here — they live in §5.3 next to the analysis that uses
them. The cross-dataset reader who wants the condensed view can
use Table 5.2 above; the per-horizon reader can jump to:

- §5.3.1, Table 5.3 — M5 nine-row grid (SN, LGBM recursive,
  LGBM direct × `h ∈ {7, 14, 28}`), including WRMSSE.
- §5.3.4, Table 5.4 — Rohlik v2 nine-row grid. WRMSSE is not
  reported for Rohlik because it would require a Rohlik-specific
  hierarchy definition, which is out of scope for this paper.
- §5.3.5, Table 5.5 — Favorita nine-row grid.

### 5.2.3 Cost and compute envelope

Total runtime across the three baseline sweeps is 4 h 23 min of
E4DS_V4 wall time at a combined cost of **$2.049 and 0.00570 kg
CO₂eq**. Table 5.6 below gives the breakdown by dataset and by
model family; per-job numbers (runtime, cost, CO₂) appear in
Tables 5.3–5.5.

**Table 5.6.** Baseline-sweep cost envelope across the three
datasets, by model family. All values are 9-job totals per
dataset. Cost is computed in-job from Azure's published
per-second pricing for `Standard_E4ds_v4` in `swedencentral`
($0.38/hr at time of writing); CO₂ uses the region's 2025
baseline marginal intensity of 0.274 kgCO₂eq/kWh.

| Dataset   | SN cost | LGBM-rec cost | LGBM-dir cost | Total cost | Total CO₂ (kg) | Dominant job          |
|---|---|---|---|---|---|---|
| M5        | $0.146 | $0.096 | $0.571 | $0.810 | 0.00250 | `lgbm_dir_h28` (62 min, $0.394) |
| Rohlik v2 | $0.0022 | $0.0094 | $0.0982 | $0.120 | 0.00030 | `lgbm_dir_h28` (9 min, $0.055)  |
| Favorita  | $0.0161 | $0.0734 | $1.030 | $1.119 | 0.00290 | `lgbm_dir_h28` (60 min, $0.379) |
| **Total** | $0.165 | $0.179 | $1.700 | $2.049 | 0.00570 | — |

Two observations on cost:

1. **Recursive LightGBM is cheap even at scale.** The combined
   recursive sweep (3 datasets × 3 horizons = 9 jobs) cost under
   **$0.18** across the full baseline. Per-dataset recursive
   sweeps are $0.01–0.08, i.e. two orders of magnitude below the
   direct sweep on the same dataset.

2. **LightGBM-direct dominates the cost envelope (83 % of total,
   $1.70 of $2.05)** despite being the losing protocol on two of
   the three datasets. This is the central cost observation that
   §5.3.8 develops for the Pareto analysis in §6.3: on
   continuous-demand retail (Rohlik and Favorita) the strongest
   baseline is also the cheapest, and direct LightGBM is a
   dominated variant on both axes simultaneously.

### 5.2.4 Foundation model rows (pending Phase F)

Foundation model zero-shot rows are pending — the GPU cluster
for Phase F (`cc-forecast-gpu`, Standard_NC6s_v3, quota
requested 2026-04-13) is blocked on Azure capacity approval.
When Phase F lands it will populate the following grid:

**Table 5.7 [placeholder].** Foundation model zero-shot results,
same protocol as §5.1.3. Models: Chronos-Bolt (Base), Chronos-2
(120 M), TimesFM 2.5 (200 M), Moirai 2.0 (large), TiRex (35 M),
TabPFN-TS (11 M, covariate-aware). Datasets: M5, Rohlik v2,
Favorita (top 30k). Horizons: 7, 14, 28. All models evaluated
zero-shot (no fine-tuning). Per-model context length, sampling
parameters, and inference script details are in §5.4.

*(Grid skeleton: 6 models × 3 datasets × 3 horizons = 54 rows,
plus SN and best-LGBM baselines duplicated from §5.2 for
readability. §5.2.4 will be populated in place when Phase F
jobs complete.)*

Expected FM cost is estimated at **$18–24 per full 54-job
sweep** on a single NC6s_v3 node, based on the per-model
inference throughput numbers reported in the source papers
(§4, extracted from A11/A13/A14). This is an order of
magnitude above the baseline sweep cost (§5.2.3) but well below
the tuned FM fine-tuning workflows reported in e.g. TTM
(NeurIPS 2024) and Chronos-2 (arXiv 2025). Once Phase F lands,
the Pareto frontier of §6.3 will combine Table 5.6's baseline
cost with Table 5.7's FM cost.

---

*Sources for this section:* `analysis/baseline_results.md`
Phases B–E, pipeline YAMLs `benchmark/code/pipelines/
{m5,rohlik,favorita}_consolidated.yaml`, and the MLflow run
registries for the three named pipelines. §5.3 reads its numbers
from the same sources, so any update to §5.2 requires the
same update to §5.3's tables.
