# Appendix C: Per-Series Metric Distributions

## C.1 Bootstrap Standard Errors for Source B FM Cells

Table C.1 reports the 10,000-iteration bootstrap standard error of
mean WAPE for each of the 18 Source B foundation model cells
(Chronos-Bolt-Tiny and TiRex × 3 datasets × 3 horizons). Each cell
samples 100 series (98–100 after WAPE filtering). The bootstrap
validates that n = 100 produces stable WAPE estimates for the
meta-regression of §6.

**Table C.1.** Bootstrap standard error and 95% CI for Source B FM
cells. Two rows per (dataset, horizon) cell correspond to
Chronos-Bolt-Tiny and TiRex respectively.

| Dataset  | Horizon | n_valid | WAPE mean | Bootstrap SE | 95% CI lower | 95% CI upper | CI width |
|----------|---------|---------|-----------|-------------|-------------|-------------|----------|
| Favorita | 7       | 100     | 0.525     | 0.008       | 0.510       | 0.540       | 0.030    |
| Favorita | 7       | 100     | 0.532     | 0.008       | 0.517       | 0.547       | 0.029    |
| Favorita | 14      | 100     | 0.537     | 0.008       | 0.522       | 0.553       | 0.031    |
| Favorita | 14      | 100     | 0.531     | 0.008       | 0.515       | 0.547       | 0.031    |
| Favorita | 28      | 98      | 0.540     | 0.008       | 0.524       | 0.555       | 0.031    |
| Favorita | 28      | 98      | 0.546     | 0.008       | 0.531       | 0.561       | 0.030    |
| M5       | 7       | 100     | 0.934     | 0.011       | 0.912       | 0.956       | 0.044    |
| M5       | 7       | 100     | 0.958     | 0.012       | 0.933       | 0.981       | 0.048    |
| M5       | 14      | 100     | 0.937     | 0.011       | 0.915       | 0.957       | 0.042    |
| M5       | 14      | 100     | 0.956     | 0.012       | 0.933       | 0.978       | 0.045    |
| M5       | 28      | 100     | 0.956     | 0.011       | 0.934       | 0.976       | 0.042    |
| M5       | 28      | 100     | 0.942     | 0.010       | 0.921       | 0.961       | 0.040    |
| Rohlik   | 7       | 98      | 0.322     | 0.011       | 0.301       | 0.344       | 0.043    |
| Rohlik   | 7       | 98      | 0.314     | 0.011       | 0.293       | 0.336       | 0.043    |
| Rohlik   | 14      | 98      | 0.326     | 0.012       | 0.305       | 0.350       | 0.045    |
| Rohlik   | 14      | 98      | 0.334     | 0.012       | 0.312       | 0.358       | 0.046    |
| Rohlik   | 28      | 98      | 0.345     | 0.013       | 0.321       | 0.372       | 0.051    |
| Rohlik   | 28      | 98      | 0.353     | 0.014       | 0.327       | 0.380       | 0.053    |

Median bootstrap SE across all 18 cells: 0.011. Widest 95% CI:
±0.027 WAPE (Rohlik h = 28). Interpretation:

- The M5 FM-vs-LGBM gap of 40+ pp WAPE is stable to >10 SE.
- The Rohlik gap of 4–8 pp is stable to 3–6 SE.
- The Favorita "close call" of 0.3 pp at h = 7 is within 1 SE and
  should be interpreted as indistinguishable from zero at n = 100.

## C.2 M5 Per-Series WAPE Tail Analysis

On M5, approximately 70% of the 30,490 series have zero-day
fractions exceeding 50%. For these intermittent series, the
per-series WAPE denominator (sum of actuals in the evaluation
window) can be very small, producing extreme WAPE values that
dominate the mean. Specifically:

- The top 1% of per-series WAPE values (LightGBM recursive, h = 28)
  range from 15.2 to 412.7, compared to a median of 0.89.
- Dropping the top 1% of series reduces mean WAPE from 1.94 to 1.12
  (a 42% reduction), demonstrating that the mean is dominated by
  the tail.
- Foundation models produce lower per-series WAPE on these
  zero-heavy series because their predictions are closer to zero
  (a trivial prediction for intermittent demand), not because they
  forecast the non-zero events more accurately.

This tail behaviour is the mechanism behind the M5 WAPE artefact
documented in §5.4.5 and is the reason we exclude M5 WAPE cells
from the primary meta-regression intercept (§6.7, excl-M5 model).
The M5 WRMSSE metric, which uses a hierarchical weighting scheme,
does not suffer from this pathology and shows FM performing worse
than LightGBM (Δ = +0.41).
