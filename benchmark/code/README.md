# Benchmark Code

This directory contains the Python implementation used for the paper's Source B
experiments.

## Layout

```text
benchmark/code/
├── config/              # experiment configuration
├── data/loaders/        # M5, Favorita, Rohlik, fev-bench, GIFT-Eval loaders
├── evaluation/          # rolling evaluation, metrics, WRMSSE, cost accounting
├── experiments/         # runnable experiment entry points and sweep scripts
├── models/              # baseline, ML, and foundation-model wrappers
├── pipelines/           # Azure ML pipeline YAMLs
├── environment*.yaml    # Azure/CPU conda environments
└── requirements-local-fm.txt
```

## Main Entry Points

- `experiments/run_gap_filling.py` - generic runner for baseline and selected
  model cells.
- `experiments/run_local_fm_sweep.sh` - local MacBook foundation-model sweep.
- `experiments/run_m5_full.sh` - M5 Source B sweep.
- `experiments/run_rohlik_full.sh` - Rohlik v2 Source B sweep.
- `experiments/run_favorita_full.sh` - Favorita Source B sweep.
- `experiments/run_direct_scaled_favorita.py` - horizon-scaled direct-LightGBM
  robustness check.

## Result Export

MLflow runs are consolidated by:

```bash
python tools/export_mlflow_to_csv.py \
  --azure-uri "$AZURE_MLFLOW_URI" \
  --out benchmark/results/local_fm_sweep.csv
```

Use `--azure-uri ""` for local-only export. The checked-in
`benchmark/results/local_fm_sweep.csv` is the table used by the manuscript.

## Raw Data

Raw datasets are not committed. Download them from Kaggle/Rohlik and place them
under `data/raw/`; the loaders expect that local layout.

## Notes for Reviewers

The experiment code is included for auditability and reruns. The fastest way to
reproduce the manuscript claims is to rerun `analysis/meta_regression.R` against
the checked-in extraction/result CSV files.
