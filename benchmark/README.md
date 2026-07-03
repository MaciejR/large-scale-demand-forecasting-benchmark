# Benchmark Components

This directory contains the Source B experiment code and exported results used
by the paper.

## Contents

- `code/` - Python experiment implementation.
- `results/local_fm_sweep.csv` - consolidated Source B result table used by
  `analysis/meta_regression.R`.
- `results/direct_scaled_favorita.csv` - robustness check for horizon-scaled
  direct LightGBM on Favorita.
- `evaluation.md` - early benchmark design notes.

## Source B Scope

The paper does not claim that Source B is a full public leaderboard. It is a
gap-filling experiment that anchors:

- local consumer-hardware foundation-model inference,
- Azure CPU LightGBM/statistical baselines,
- cost and CO2 accounting,
- matched retail cells for M5, Favorita, and Rohlik v2.

The primary statistical mass in the paper comes from Source A extraction
(fev-bench, GIFT-Eval, and literature rows). Source B is used for controlled
gap filling and cost analysis.
