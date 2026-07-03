# Reproducing the Paper Results

This document is intended for collaborators reviewing the manuscript and code.
It focuses on reproducing the tables and figures used in the paper, not on
rerunning every expensive model sweep from scratch.

## Environment

The meta-analysis requires R with:

- `tidyverse`
- `metafor`
- `ggplot2`

The benchmark code uses Python 3.11. The main environments are:

- `benchmark/code/environment_cpu.yaml` for CPU baseline experiments.
- `benchmark/code/requirements-local-fm.txt` for local foundation-model runs.

## Rebuild the Meta-Regression Outputs

From the repository root:

```bash
Rscript analysis/meta_regression.R
```

Inputs:

- `analysis/extraction_schema.csv`
- `benchmark/results/local_fm_sweep.csv`
- `analysis/figures/table_bootstrap_se.csv` when available

Key outputs:

- `analysis/figures/table_6_1_model_level_deltas.csv`
- `analysis/figures/table_6_1_model_level_deltas_best_baseline.csv`
- `analysis/figures/table_6_1_primary_intercept.txt`
- `analysis/figures/sensitivity_*.txt`
- `analysis/figures/figure_6_*.pdf`

Expected headline result:

- Primary pooled estimate: `Delta = -0.195`, 95% CI `[-0.283, -0.107]`,
  `p < .0001`, `k = 543`.
- Best conventional baseline sensitivity: `Delta = -0.155`, 95% CI
  `[-0.231, -0.078]`, `p < .0001`, `k = 543`.

Negative values mean the foundation model has lower error than the conventional
baseline.

## Rebuild the Manuscript

From `paper/latex/`:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The checked-in PDF is `paper/latex/main.pdf`.

## Rerun Source B Experiments

The paper's Source B experiments combine:

- local MacBook foundation-model sweeps,
- Azure CPU LightGBM/statistical baseline sweeps,
- exported MLflow results in `benchmark/results/local_fm_sweep.csv`.

Rerunning the full Source B sweep is compute- and data-dependent. The relevant
entry points are:

- `benchmark/code/experiments/run_local_fm_sweep.sh`
- `benchmark/code/experiments/run_m5_full.sh`
- `benchmark/code/experiments/run_rohlik_full.sh`
- `benchmark/code/experiments/run_favorita_full.sh`
- `tools/export_mlflow_to_csv.py`

The exporter no longer hard-codes a private Azure workspace URI. To export from
Azure MLflow, pass it explicitly:

```bash
python tools/export_mlflow_to_csv.py \
  --azure-uri "$AZURE_MLFLOW_URI" \
  --out benchmark/results/local_fm_sweep.csv
```

Pass `--azure-uri ""` to export only local MLflow runs.

## Raw Data

Raw competition data are intentionally not tracked in git. Place downloads under
`data/raw/` using the dataset-specific loaders in `benchmark/code/data/loaders/`.
The `.gitignore` excludes these files.

## Tests

Lightweight checks:

```bash
pytest
```

Some model-wrapper tests may skip or fail if optional foundation-model packages
or raw datasets are not installed locally. The meta-regression and manuscript
build are the primary reproducibility checks for the paper.
