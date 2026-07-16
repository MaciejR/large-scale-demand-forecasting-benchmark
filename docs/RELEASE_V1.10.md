# Release Notes: v1.10 TiRex fev-bench WAPE Covariance Repair

Release commit: to be filled after commit.

Local package target:
`release/zenodo-v1.10-tirex-fev-bench-wape-covariance-repair.zip`

## Summary

v1.10 extends the fev-bench prediction-level WAPE covariance repair to TiRex.
The repaired Source A slice now has official fev-bench retail reruns against
Seasonal Naive for Chronos-Bolt-Tiny, Chronos-2, and TiRex across all 20 retail
tasks.  Each FM has 179,258 matched series-window forecast units and an
empirical paired-bootstrap 20 by 20 WAPE log-ratio covariance matrix.

TiRex outputs are point forecasts replicated to quantile columns by the official
runner, so this repair supports WAPE/MAE paired analyses, not repaired SQL
inference.  SQL, MASE, GIFT-Eval, stronger best-baseline comparisons, and other
FM families remain descriptive until comparable prediction-level covariance is
generated.

## What Changed

- Completed `fev_v1_10_tirex_official_retail` for all 20 fev-bench retail
  tasks.
- Added TiRex batch support for ragged fev histories without leading padding.
- Added generic point-forecast batch output handling to the official fev runner.
- Added TiRex paired WAPE bootstrap outputs:
  - task-level contrasts,
  - bootstrap draws,
  - covariance matrix,
  - long-form covariance table,
  - joined paired units.
- Added `analysis/fev_bench_wape_summary.py` to regenerate the manuscript
  summary table from contrast files.
- Updated README, ARTIFACTS, REPRODUCING, manuscript abstract, Section 6,
  limitations, and the compiled PDF.

## Main Results

Official fev-bench retail coverage:

| Model | Completed tasks | Forecasts |
| --- | ---: | ---: |
| Seasonal Naive | 20/20 | 179,258 |
| Chronos-Bolt-Tiny | 20/20 | 179,258 |
| Chronos-2 | 20/20 | 179,258 |
| TiRex | 20/20 | 179,258 |

Paired WAPE bootstrap summaries:

| Model | Tasks | Paired units | Median log-ratio | Mean log-ratio | FM better | CI favours FM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Chronos-Bolt-Tiny | 20 | 179,258 | -0.213 | -0.183 | 16/20 | 16/20 |
| Chronos-2 | 20 | 179,258 | -0.268 | -0.305 | 20/20 | 18/20 |
| TiRex | 20 | 179,258 | -0.275 | -0.300 | 19/20 | 19/20 |

Negative log-ratios favour the foundation model.

## Included Artifacts

Tracked source and lightweight outputs:

- `analysis/fev_bench_official_manifest.py`
- `analysis/fev_bench_prediction_report.py`
- `analysis/fev_bench_wape_summary.py`
- `analysis/figures/fev_official_run_manifest.csv`
- `analysis/figures/fev_official_model_coverage.csv`
- `analysis/figures/fev_official_bootstrap_manifest.csv`
- `analysis/figures/fev_prediction_level_wape_summary.csv`
- `analysis/figures/fev_prediction_level_wape_summary.tex`
- `analysis/figures/fev_chronos_bolt_paired_wape_*.csv`
- `analysis/figures/fev_chronos2_paired_wape_*.csv`
- `analysis/figures/fev_tirex_paired_wape_*.csv`
- `paper/latex/main.pdf`

Excluded from git and release packages:

- raw datasets,
- local logs,
- MLflow stores,
- checkpoints,
- private documents,
- LaTeX build products,
- parquet prediction files,
- full local `benchmark/results/fev_bench_official/` prediction tree.

The full prediction tree can be regenerated from `REPRODUCING.md`.

## Validation

Last local validation:

- `pytest`: 23 passed, 12 skipped.
- `python -m py_compile` for fev-bench runner/report/summary scripts.
- `git diff --check`.
- `pdflatex && bibtex && pdflatex && pdflatex`.
- LaTeX log scan: no undefined citations or references.
- fev-bench coverage/bootstrap sanity:
  - 20/20 tasks for all four official rerun models,
  - 179,258 forecasts per model,
  - 15 complete bootstrap artifact records,
  - 179,258 paired units per FM contrast set,
  - 20 by 20 covariance matrices.

## GitHub Release Draft

Suggested tag: `v1.10-tirex-fev-bench-wape-covariance-repair`

Suggested title:
`v1.10 TiRex fev-bench WAPE covariance repair`

Suggested release notes:

```text
This repair release extends prediction-level fev-bench WAPE covariance to
TiRex. Chronos-Bolt-Tiny, Chronos-2, and TiRex now each have official
fev-bench retail reruns against Seasonal Naive across all 20 retail tasks,
179,258 paired series-window units, paired WAPE bootstrap contrasts, bootstrap
draws, and empirical 20x20 covariance matrices.

Scope: this repairs the WAPE Source A slice. TiRex uses point forecasts
replicated to quantile columns, so SQL and MASE inference, GIFT-Eval,
best-baseline comparisons, and additional FM families remain descriptive until
comparable prediction-level covariance is generated.

Validation: pytest passed locally (23 passed, 12 skipped); LaTeX build passed;
coverage/bootstrap sanity checks passed.
```

## Zenodo Metadata Draft

```json
{
  "title": "When Do Foundation Models Pay Off for Retail Demand Forecasting? v1.10 TiRex fev-bench WAPE Covariance Repair",
  "upload_type": "publication",
  "publication_type": "technicalnote",
  "creators": [
    {
      "name": "Rubczynski, Maciej"
    }
  ],
  "description": "v1.10 repair package for a PRISMA-informed exploratory cross-benchmark reanalysis of foundation models in retail demand forecasting. This version extends prediction-level paired WAPE bootstrap covariance matrices for official fev-bench retail contrasts against Seasonal Naive to TiRex, alongside Chronos-Bolt-Tiny and Chronos-2, across all 20 retail tasks. The repair addresses paired sampling dependence for this Source A WAPE slice while keeping SQL, MASE, GIFT-Eval, best-baseline comparisons, and additional foundation-model families descriptive until comparable prediction-level covariance is generated.",
  "keywords": [
    "demand forecasting",
    "foundation models",
    "retail",
    "time series",
    "benchmark reanalysis",
    "fev-bench",
    "bootstrap covariance",
    "reproducibility"
  ],
  "version": "v1.10-tirex-fev-bench-wape-covariance-repair",
  "language": "eng",
  "license": "cc-by-4.0"
}
```
