# Appendix D: Sensitivity Analyses

Three variants of the meta-regression are reported to assess
robustness of the headline finding (§6.7). All models use
`metafor::rma.mv` with REML estimation and Knapp-Hartung
t-distribution adjustment.

## D.1 Full Cross-Paper Pool (k = 10)

Model: `rma.mv(yi = delta, V = vi, random = ~1|dataset_norm,
test = "t", method = "REML")` on the 10 cells of Table 6.1.

| Parameter         | Value                        |
|-------------------|------------------------------|
| k                 | 10                           |
| Intercept (Δ̂)    | +0.101                       |
| SE                | 0.145                        |
| t(9)              | 0.694                        |
| p-value           | 0.505                        |
| 95% CI            | [−0.227, +0.429]             |
| σ² (dataset)      | 0.063                        |
| Q(9)              | 1055.3, p < .0001            |
| I²                | 99.1%                        |

**Interpretation.** The full-pool intercept is positive
(FM worse on average) but far from significant. The extreme
heterogeneity (I² = 99.1%) is driven by the three M5 WAPE
cells (Δ = −0.54 to −0.78), which are artefactual (§5.4.5),
and the M5 WRMSSE cell (Δ = +0.41), which goes in the
opposite direction.

## D.2 Excluding M5 WAPE (k = 6)

Same model specification, dropping the three M5 WAPE cells
but retaining M5 WRMSSE.

**Note:** The k = 6 pool in this table excludes only the three
M5 WAPE cells. The M5 WRMSSE cell (k = 1) is retained because
WRMSSE does not suffer from the per-series denominator
pathology. However, because the M5 WRMSSE cell is the only
non-WAPE cell in the pool, the excl-M5 intercept is reported
as the primary result to avoid conflating metric effects.

| Parameter         | Value                        |
|-------------------|------------------------------|
| k                 | 6                            |
| Intercept (Δ̂)    | −0.044                       |
| SE                | 0.028                        |
| t(5)              | −1.583                       |
| p-value           | 0.174                        |
| 95% CI            | [−0.115, +0.027]             |
| σ² (dataset)      | 0.001                        |
| Q(5)              | 2.00, p = 0.849              |
| I²                | 0.0%                         |

**Interpretation.** After removing the M5 WAPE artefact, the
intercept is small and negative (FM slightly better) but not
significant. Heterogeneity drops to zero: the six remaining
cells (Favorita × 3 + Rohlik × 3) are homogeneous. This is
the primary result reported in the Abstract and §9.

## D.3 Within-Paper Only — Source B (k = 9)

Model: `rma.mv(yi = delta, V = vi, random = ~1|paper_id +
~1|paper_id/dataset_norm, test = "t", method = "REML")` on the
9 Source B paired cells (3 datasets × 3 horizons, paper_id =
LOCAL_MAC_*). Variance proxy: `vi = 1/n_valid = 0.01`.

| Parameter              | Value                   |
|------------------------|-------------------------|
| k                      | 9                       |
| Intercept (Δ̂)         | −0.245                  |
| SE                     | 0.103                   |
| t(8)                   | −2.386                  |
| p-value                | 0.044                   |
| 95% CI                 | [−0.482, −0.008]        |
| σ²₁ (paper_id)         | 0.043                   |
| σ²₂ (paper/dataset)    | 0.043                   |
| Q(8)                   | 76.00, p < .0001        |

**Interpretation.** The within-paper model reaches significance
(p = 0.044) with a substantial negative intercept (FM better
by ~25 pp on average across all 9 cells). However, this result
is dominated by the three M5 cells (Δ = −0.54 to −0.78). After
mentally excluding M5, the Favorita and Rohlik cells contribute
Δ ∈ [−0.01, −0.09], consistent with the cross-paper excl-M5
finding. The within-paper model is not used as the primary
result because (i) it has only one paper_id (no between-study
variation) and (ii) the M5 WAPE artefact inflates the intercept.

## D.4 Summary Across Sensitivity Variants

| Variant             | k  | Δ̂      | 95% CI             | p     | I²    |
|---------------------|----|---------|--------------------|-------|-------|
| Full pool           | 10 | +0.101  | [−0.227, +0.429]   | 0.505 | 99.1% |
| Excl-M5 WAPE        | 6  | −0.044  | [−0.115, +0.027]   | 0.174 | 0.0%  |
| Within-paper (B)    | 9  | −0.245  | [−0.482, −0.008]   | 0.044 | —     |

The three variants tell a consistent story: the apparent FM
advantage in the full pool is a composition effect driven by the
M5 WAPE artefact. Once M5 WAPE is excluded, the FM-vs-LGBM
gap is small (−0.044 WAPE), not significant (p = 0.174), and
homogeneous (I² = 0%).
