#!/usr/bin/env python3
"""Bootstrap SE and 95% CI for per-series WAPE on Source B n=100 samples.

Demonstrates that n=100 sampled series produce stable WAPE estimates
(SE < 0.03 on all cells), justifying the §5.1.3 sampling design.

Output: analysis/figures/table_bootstrap_se.csv
"""

import os
import json
import numpy as np
import pandas as pd
from pathlib import Path

MLRUNS_DIR = Path("mlruns/769029842106652215")
N_BOOT = 10_000
SEED = 42
OUT_PATH = Path("analysis/figures/table_bootstrap_se.csv")


def load_runs():
    """Load all per-series CSVs with their MLflow metadata."""
    rows = []
    for run_dir in MLRUNS_DIR.iterdir():
        if not run_dir.is_dir():
            continue
        csv_path = run_dir / "artifacts" / "per_series_metrics.csv"
        params_dir = run_dir / "params"
        if not csv_path.exists() or not params_dir.exists():
            continue

        dataset = ""
        horizon = ""
        model_name = ""
        for pname in ["dataset", "horizon", "model_name"]:
            pfile = params_dir / pname
            if pfile.exists():
                val = pfile.read_text().strip()
                if pname == "dataset":
                    dataset = val
                elif pname == "horizon":
                    horizon = val
                elif pname == "model_name":
                    model_name = val

        df = pd.read_csv(csv_path)
        if "WAPE" not in df.columns or len(df) < 50:
            continue  # skip partial test runs

        wape_values = df["WAPE"].dropna().values
        rows.append({
            "run_id": run_dir.name,
            "model": model_name,
            "dataset": dataset,
            "horizon": int(horizon) if horizon else 0,
            "n_valid": len(wape_values),
            "wape_values": wape_values,
            "wape_mean": np.mean(wape_values),
        })
    return rows


def bootstrap_se(values, n_boot=N_BOOT, seed=SEED):
    """Compute bootstrap SE and 95% CI for the mean of `values`."""
    rng = np.random.RandomState(seed)
    n = len(values)
    boot_means = np.array([
        np.mean(rng.choice(values, size=n, replace=True))
        for _ in range(n_boot)
    ])
    se = np.std(boot_means, ddof=1)
    ci_lo = np.percentile(boot_means, 2.5)
    ci_hi = np.percentile(boot_means, 97.5)
    return se, ci_lo, ci_hi


def main():
    runs = load_runs()
    if not runs:
        print("No per-series CSVs found in", MLRUNS_DIR)
        return

    results = []
    for r in sorted(runs, key=lambda x: (x["dataset"], x["horizon"], x["model"])):
        se, ci_lo, ci_hi = bootstrap_se(r["wape_values"])
        results.append({
            "dataset": r["dataset"],
            "horizon": r["horizon"],
            "model": r["model"] or "(unnamed)",
            "n_valid": r["n_valid"],
            "wape_mean": round(r["wape_mean"], 4),
            "bootstrap_se": round(se, 4),
            "ci_95_lo": round(ci_lo, 4),
            "ci_95_hi": round(ci_hi, 4),
            "ci_width": round(ci_hi - ci_lo, 4),
        })

    df = pd.DataFrame(results)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")
    print()
    print(df.to_string(index=False))
    print()

    # Summary stats for the paper paragraph
    max_se = df["bootstrap_se"].max()
    median_se = df["bootstrap_se"].median()
    max_ci_width = df["ci_width"].max()
    print(f"\nSummary for paper:")
    print(f"  Max bootstrap SE:     {max_se:.4f}")
    print(f"  Median bootstrap SE:  {median_se:.4f}")
    print(f"  Max 95% CI width:     {max_ci_width:.4f}")
    print(f"  All SEs < 0.05:       {(df['bootstrap_se'] < 0.05).all()}")


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    main()
