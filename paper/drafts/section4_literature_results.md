# §4 Literature Results (v0.1 draft — 2026-04-16)

This section reports the outcome of the PRISMA search and describes
the 185-row extraction before the gap-filling experiments (§5) and
meta-regression (§6) operate on it.

### 4.1 PRISMA flow

*[Figure 4.1 placeholder — PRISMA flow diagram to be rendered from
the numbers below.]*

| Stage | Count | Notes |
|-------|------:|-------|
| Records identified | ~150 | Scopus + Google Scholar + Semantic Scholar + arXiv |
| Duplicates removed | ~30 | Cross-database overlap, especially arXiv ↔ Scopus |
| Records screened (title/abstract) | ~120 | |
| Excluded at screening | ~50 | Non-retail, no quantitative results, financial only |
| Full-text assessed | ~70 | |
| Excluded at full-text | ~32 | No retail dataset, no FM evaluation, duplicate results |
| Studies included | 38 | 32 external papers + 6 own experiment blocks |
| Extraction rows | 185 | Multiple rows per study (model × dataset × metric) |

The 38 included studies break down as follows:
- **Category A (FM papers):** 17 papers, 58 rows. These are the
  primary FM technical reports — Chronos (A01), Chronos-2 (A02),
  TimesFM (A03–A04), Moirai (A05–A06), TiRex (A13), TabPFN-TS
  (A14), and the smaller FM entries (A07–A11, A15–A17).
- **Category B (benchmark papers):** 4 papers, 40 rows. GIFT-Eval
  (B01), fev-bench (B02), and two multi-model comparison papers
  (B03, B07–B08).
- **Category C (retail ML/DL papers):** 8 papers, 31 rows.
  M5 competition analyses (C01, C05), transformer-based retail
  studies (C03, C06), AutoML baselines (C10), and cross-domain
  comparisons (C04, C12).
- **Category D (cross-domain):** 3 papers, 3 rows. Included for
  model-family coverage but not in the retail-scoped meta-regression.
- **Category F (fev-bench entries):** 1 paper, 8 rows.
- **OWN_* (own experiments):** 6 experiment blocks, 45 rows.
  LightGBM baselines (§5.2–5.3) and Seasonal Naive across three
  datasets and three evaluation protocols.

### 4.2 Descriptive statistics

**Temporal distribution.** The extraction skews heavily toward
2024–2026: 79 rows from 2025 papers, 53 from 2026, 33 from 2024.
Pre-2024 rows (20 total) are almost entirely M5 competition entries
(2020–2022) and early DL comparisons. This reflects the recency of
the FM wave — the first Chronos paper appeared in late 2023, and the
bulk of FM evaluation literature dates from mid-2024 onward.

**Dataset distribution.** M5 dominates with 40 rows (22 % of the
extraction), followed by fev-bench (33 rows, 18 %), GIFT-Eval (24
rows, 13 %), and our three retail datasets (Favorita 10, Rohlik 10,
Walmart 2). The remaining rows cover cross-domain or unnamed datasets.
The concentration on M5 is partly an artefact of the M5 competition's
longevity (every retail ML paper since 2020 benchmarks on it) and
partly a genuine signal that M5 is the only public retail dataset
with enough community coverage to populate a cross-paper comparison.

**Model family distribution.** Foundation models account for 76 rows
(41 %), followed by statistical (26 rows, 14 %), ML/ML_TREE (25 + 5
= 30 rows, 16 %), deep learning (13 rows, 7 %), and various
mixed/comparison/hybrid categories (40 rows, 22 %). The high FM share
reflects the search strategy's emphasis on FM papers (block 1 of the
query); the OWN_* baseline rows partially offset the imbalance by
contributing 45 ML_TREE + STATS rows.

**Metric heterogeneity.** The extraction contains 18 distinct metric
names. The most common are WRMSSE (23 rows, mostly M5), WAPE (18
rows, mostly Source B and retail), win_rate_SQL (15 rows, fev-bench),
MASE (13 rows), MAE_mean (9 rows), and avg_rank (8 rows). 14 rows
carry `metric_name = "--"` (comparison or qualitative rows with no
single numeric metric). This metric heterogeneity is a key challenge
for the meta-regression: the cross-paper pooled Δ (§6.1) can only
operate within a single metric scale, so each (dataset, horizon,
metric) bucket must be metric-homogeneous. In practice, this means
the primary regression runs on WAPE buckets (k = 9) and a single
M5 long WRMSSE bucket (k = 1), for a total of k = 10.

**Evaluation protocol.** Three protocols appear in roughly equal
proportion: rolling origin (46 rows), rolling-tail (39 rows), and
fixed origin (38 rows). The remaining rows have no explicit protocol
label. Rolling and rolling-tail are our matched Source B protocol
(§5.1.3); fixed-origin rows from Source A may not be directly
comparable but are included in the cross-paper pool where they
share a (dataset, metric) bucket with rolling-origin rows. This is
a known threat to validity (§5.4.8).

### 4.3 Narrative synthesis by model family

**Foundation models.** The 76 FM rows paint a consistent picture on
benchmark suites: Chronos-2, TimesFM 2.5, and Moirai 2.0 achieve
win rates of 75–84 % against statistical baselines on GIFT-Eval, and
skill scores of 20–35 on fev-bench. However, almost none of these
rows report per-series WAPE on an individual retail dataset
(M5, Favorita, Rohlik) under a rolling-origin protocol. Only two
Source A FM rows land in the retail-scoped meta-regression:
C05 (TEMPO baseline, WRMSSE 0.97 on M5 h = 28) and C03 (TimesFM
on Rohlik, MASE+sMAPE with no numeric WAPE). This means that **the
FM side of the retail meta-regression is almost entirely populated
by Source B** — a structural limitation documented in §6.7.

**Gradient-boosted trees (ML_TREE).** The 30 ML_TREE rows split
between M5 competition entries (C01, 7 rows with WRMSSE 0.52–0.54
for the top-5 solutions) and our own LightGBM baselines (OWN_*,
23 rows across three datasets with WAPE and WRMSSE). Source A
ML_TREE rows are concentrated on M5 WRMSSE, where competition-grade
LightGBM achieves 0.52 — materially better than any FM row on the
same metric (Chronos at 0.97, from C05). This WRMSSE reading is
the mirror image of the WAPE reading on the same dataset, where
LGBM posts 1.35–1.94 (per-series) vs FM at 0.93–0.96 — the
metric choice determines the sign of the FM-vs-ML_TREE comparison
on M5.

**Statistical models.** The 26 STATS rows are mostly our own
Seasonal Naive baselines (OWN_*, 20 rows) plus 1 Croston row from
the M5 competition (C01) and a few MASE/sMAPE entries from
cross-domain papers. Seasonal Naive provides the universal
comparison floor: on Favorita and Rohlik, both FM and ML_TREE beat
it comfortably (by 8–15 pp WAPE); on M5, Seasonal Naive at
1.31–1.33 WAPE actually beats lightgbm_cov (1.62–1.94) at longer
horizons — a striking failure of the tree baseline documented in
§5.3 and §5.4.5.

**Deep learning.** The 13 NN rows include M5 competition entries
(DeepAR at WRMSSE 0.56 from C01, and PatchTST variants from C05)
and transformer comparisons on M5 (C06). None of these rows share
a (dataset, metric) bucket with FM rows in a way that enables
direct FM-vs-NN comparison in the meta-regression. An FM-vs-NN
analysis is possible on GIFT-Eval skill scores but is outside the
retail scope of this paper.

### 4.4 Structural finding: no within-paper FM-vs-ML_TREE pairing in the retail literature

The single most important observation from the extraction is
negative — and is itself a contribution of this review: **no
Source A paper in the retail slice reports both FM and ML_TREE
results under a shared paper identifier and a common per-series
metric.** The FM papers (Category A) evaluate FMs against
statistical baselines or against other FMs on benchmark suites,
not against well-tuned LightGBM on individual retail datasets.
The ML_TREE papers (Category C) predate the FM wave or focus on
competition results without FM comparisons. The benchmark papers
(Category B) include both families but on aggregate skill scores
that cannot be decomposed to (dataset, horizon) cells.

This gap has two consequences. First, it is the reason Source B
exists (§3.3): answering "do FMs beat LightGBM on retail data?"
requires original experiments because the literature does not
contain the comparison. Second, it means the cross-paper pooled
analysis (§6.1) is a **systematic review augmented with original
experiments**, not a classical meta-analysis of homogeneous effect
sizes. The FM side of the retail comparison is populated almost
entirely by Source B; the ML_TREE side draws on both Source A
(competition-grade results) and Source B (our own baselines).
This asymmetry is inherent to the current state of the FM
literature — it is the gap our study fills, not a design flaw.
We report the pooled estimate with and without Source B rows
in §6.7 so readers can assess each source's contribution.
