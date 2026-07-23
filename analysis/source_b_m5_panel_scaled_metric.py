"""Compute an M5-style scaled-error sensitivity for the matched M5 panel.

Official M5 WRMSSE is defined on the full coherent 12-level hierarchy.  The
Source B matched panel contains only 100 bottom-level item-store series, so this
script does not compute the official competition metric.  Instead, it computes
an origin-specific, bottom-level, dollar-weighted RMSSE on the exact prediction
panel used for the local WAPE contrasts.
"""

from __future__ import annotations

import argparse
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "analysis" / "figures" / "source_b_paired_panel_cell_summary.csv"
DEFAULT_RUN_ROOT = ROOT / "benchmark" / "results" / "source_b_paired_panel"
DEFAULT_RAW_M5 = ROOT / "data" / "raw" / "m5"
DEFAULT_OUTPUT_DIR = ROOT / "analysis" / "figures"

BASELINE_MODELS = {
    "seasonal_naive",
    "lightgbm_cov",
    "lightgbm_direct",
    "lightgbm_direct_scaled",
    "lightgbm_tuned_cov",
    "lightgbm_tuned_direct",
}
FOCUS_MODELS = ["chronos2", "tirex", "timesfm25", "moirai2", "chronos_bolt_tiny"]


def _seed(seed: int, label: str) -> int:
    return (int(seed) + zlib.crc32(label.encode("utf-8"))) % (2**32)


def load_m5_history(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sales_path = raw_dir / "sales_train_validation.csv"
    calendar_path = raw_dir / "calendar.csv"
    prices_path = raw_dir / "sell_prices.csv"
    missing = [str(path) for path in [sales_path, calendar_path, prices_path] if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing raw M5 files: " + ", ".join(missing))
    sales = pd.read_csv(sales_path)
    calendar = pd.read_csv(calendar_path)
    prices = pd.read_csv(prices_path)
    return sales, calendar, prices


def make_price_lookup(calendar: pd.DataFrame, prices: pd.DataFrame) -> dict[tuple[str, str, int], float]:
    wk_by_d = calendar[["d", "wm_yr_wk"]].copy()
    wk_by_d["d_num"] = wk_by_d["d"].str.replace("d_", "", regex=False).astype(int)
    price = prices[["store_id", "item_id", "wm_yr_wk", "sell_price"]].merge(
        wk_by_d[["wm_yr_wk", "d_num"]], on="wm_yr_wk", how="inner"
    )
    return {
        (str(row.store_id), str(row.item_id), int(row.d_num)): float(row.sell_price)
        for row in price.itertuples(index=False)
    }


def make_series_metadata(sales: pd.DataFrame) -> tuple[dict[str, np.ndarray], dict[str, tuple[str, str]]]:
    day_cols = [col for col in sales.columns if col.startswith("d_")]
    histories: dict[str, np.ndarray] = {}
    ids: dict[str, tuple[str, str]] = {}
    for row in sales.itertuples(index=False):
        series_id = str(getattr(row, "id"))
        histories[series_id] = np.asarray([getattr(row, col) for col in day_cols], dtype=float)
        ids[series_id] = (str(getattr(row, "store_id")), str(getattr(row, "item_id")))
    return histories, ids


def rmsse_scale(history: np.ndarray, origin_idx: int) -> float:
    train = history[: int(origin_idx)]
    nonzero = np.flatnonzero(train)
    if len(nonzero) == 0:
        return 1.0
    active = train[int(nonzero[0]) :]
    if len(active) < 2:
        return 1.0
    scale = float(np.mean(np.diff(active) ** 2))
    return max(scale, 1e-9)


def dollar_weight(
    history: np.ndarray,
    store_id: str,
    item_id: str,
    origin_idx: int,
    price_lookup: dict[tuple[str, str, int], float],
) -> float:
    start = max(1, int(origin_idx) - 27)
    end = int(origin_idx)
    value = 0.0
    for d_num in range(start, end + 1):
        units = float(history[d_num - 1])
        price = price_lookup.get((store_id, item_id, d_num), 0.0)
        value += units * price
    return value


def load_prediction_paths(summary_path: Path, run_root: Path) -> pd.DataFrame:
    summary = pd.read_csv(summary_path)
    m5 = summary[summary["dataset"].astype(str).str.upper().eq("M5")].copy()
    if m5.empty:
        raise ValueError(f"No M5 rows in {summary_path}")
    rows = []
    for row in m5.itertuples(index=False):
        run_dir = run_root / str(row.source_run_dir)
        path = run_dir / f"predictions_m5_h{int(row.horizon)}_{row.model_name}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Missing prediction parquet: {path}")
        rows.append(
            {
                "horizon": int(row.horizon),
                "model_name": str(row.model_name),
                "wape_aggregate": float(row.WAPE_aggregate),
                "path": path,
            }
        )
    return pd.DataFrame(rows).drop_duplicates(["horizon", "model_name", "path"])


def score_frame(
    frame: pd.DataFrame,
    histories: dict[str, np.ndarray],
    ids: dict[str, tuple[str, str]],
    price_lookup: dict[tuple[str, str, int], float],
) -> pd.DataFrame:
    required = {"series_id", "origin_idx", "horizon", "model_name", "y_true", "y_pred"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Prediction frame missing columns: {sorted(missing)}")

    rows = []
    grouped = frame.groupby(["series_id", "origin_idx", "horizon", "model_name"], sort=True)
    for (series_id, origin_idx, horizon, model_name), group in grouped:
        history = histories[str(series_id)]
        store_id, item_id = ids[str(series_id)]
        mse = float(np.mean((group["y_true"].to_numpy(float) - group["y_pred"].to_numpy(float)) ** 2))
        scale = rmsse_scale(history, int(origin_idx))
        weight = dollar_weight(history, store_id, item_id, int(origin_idx), price_lookup)
        rows.append(
            {
                "series_id": str(series_id),
                "origin_idx": int(origin_idx),
                "horizon": int(horizon),
                "model_name": str(model_name),
                "weight": weight,
                "rmsse": float(np.sqrt(mse / scale)),
            }
        )
    return pd.DataFrame(rows)


def weighted_rmsse(scored: pd.DataFrame, sampled_series: np.ndarray | None = None) -> float:
    data = scored
    if sampled_series is not None:
        sampled = pd.DataFrame({"series_id": sampled_series.astype(str), "_draw": np.arange(len(sampled_series))})
        data = sampled.merge(scored, on="series_id", how="left")
    weight_sum = float(data["weight"].sum())
    if weight_sum <= 0:
        return float(data["rmsse"].mean())
    return float(np.average(data["rmsse"], weights=data["weight"]))


def build_tables(paths: pd.DataFrame, scored: pd.DataFrame, bootstrap_draws: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    for row in paths.itertuples(index=False):
        model_scored = scored[
            (scored["horizon"].eq(int(row.horizon))) & (scored["model_name"].eq(str(row.model_name)))
        ]
        summary_rows.append(
            {
                "horizon": int(row.horizon),
                "model_name": str(row.model_name),
                "WAPE_aggregate": float(row.wape_aggregate),
                "panel_weighted_rmsse": weighted_rmsse(model_scored),
                "panel_mean_rmsse": float(model_scored["rmsse"].mean()),
                "n_series": int(model_scored["series_id"].nunique()),
                "n_origins": int(model_scored[["series_id", "origin_idx"]].drop_duplicates().shape[0]),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values(["horizon", "panel_weighted_rmsse", "model_name"])

    contrast_rows = []
    for horizon, horizon_summary in summary.groupby("horizon", sort=True):
        baseline_summary = horizon_summary[horizon_summary["model_name"].isin(BASELINE_MODELS)]
        if baseline_summary.empty:
            continue
        best = baseline_summary.sort_values(["panel_weighted_rmsse", "model_name"]).iloc[0]
        best_model = str(best["model_name"])
        best_score = float(best["panel_weighted_rmsse"])
        best_scored = scored[(scored["horizon"].eq(horizon)) & (scored["model_name"].eq(best_model))]
        series_ids = np.array(sorted(best_scored["series_id"].unique()), dtype=str)
        rng = np.random.default_rng(_seed(seed, f"m5-panel-scaled-{horizon}-{best_model}"))
        draws = {}
        for model_name in list(FOCUS_MODELS):
            if model_name not in set(horizon_summary["model_name"]):
                continue
            model_score = float(
                horizon_summary[horizon_summary["model_name"].eq(model_name)]["panel_weighted_rmsse"].iloc[0]
            )
            model_scored = scored[(scored["horizon"].eq(horizon)) & (scored["model_name"].eq(model_name))]
            boot = []
            shared_series = np.array(
                sorted(set(series_ids).intersection(set(model_scored["series_id"].unique()))), dtype=str
            )
            if len(shared_series) == 0:
                raise ValueError(f"No shared series for {model_name} h={horizon}")
            for _ in range(bootstrap_draws):
                sampled = rng.choice(shared_series, size=len(shared_series), replace=True)
                fm_draw = weighted_rmsse(model_scored, sampled)
                baseline_draw = weighted_rmsse(best_scored, sampled)
                boot.append(float(np.log(fm_draw / baseline_draw)))
            draws[model_name] = np.asarray(boot, dtype=float)
            contrast_rows.append(
                {
                    "horizon": int(horizon),
                    "model_name": model_name,
                    "best_baseline_model": best_model,
                    "fm_panel_weighted_rmsse": model_score,
                    "baseline_panel_weighted_rmsse": best_score,
                    "log_ratio": float(np.log(model_score / best_score)),
                    "ci95_low": float(np.quantile(draws[model_name], 0.025)),
                    "ci95_high": float(np.quantile(draws[model_name], 0.975)),
                    "bootstrap_draws": int(bootstrap_draws),
                    "n_series": int(len(shared_series)),
                }
            )
    contrasts = pd.DataFrame(contrast_rows).sort_values(["horizon", "log_ratio", "model_name"])
    return summary, contrasts


def write_chronos_table(contrasts: pd.DataFrame, output_path: Path) -> None:
    rows = contrasts[contrasts["model_name"].eq("chronos2")].sort_values("horizon")
    lines = [
        "% Generated by analysis/source_b_m5_panel_scaled_metric.py",
        "\\begin{tabular}{rlrrr}",
        "\\toprule",
        "$h$ & Best baseline & FM RMSSE & Baseline RMSSE & $\\ell$ [95\\% CI] \\\\",
        "\\midrule",
    ]
    for row in rows.itertuples(index=False):
        baseline = str(row.best_baseline_model).replace("_", "\\_")
        lines.append(
            f"{int(row.horizon)} & {baseline} & {row.fm_panel_weighted_rmsse:.3f} & "
            f"{row.baseline_panel_weighted_rmsse:.3f} & "
            f"{row.log_ratio:.3f} [{row.ci95_low:.3f}, {row.ci95_high:.3f}] \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--raw-m5", type=Path, default=DEFAULT_RAW_M5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260714)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sales, calendar, prices = load_m5_history(args.raw_m5)
    histories, ids = make_series_metadata(sales)
    price_lookup = make_price_lookup(calendar, prices)
    paths = load_prediction_paths(args.summary, args.run_root)
    scored_frames = []
    for row in paths.itertuples(index=False):
        pred = pd.read_parquet(row.path)
        scored_frames.append(score_frame(pred, histories, ids, price_lookup))
    scored = pd.concat(scored_frames, ignore_index=True)
    summary, contrasts = build_tables(paths, scored, args.bootstrap_draws, args.seed)
    summary.to_csv(args.output_dir / "source_b_m5_panel_scaled_metric.csv", index=False)
    contrasts.to_csv(args.output_dir / "source_b_m5_panel_scaled_metric_contrasts.csv", index=False)
    write_chronos_table(contrasts, args.output_dir / "source_b_m5_panel_scaled_metric_chronos2.tex")
    print(f"Wrote {len(summary)} summary rows and {len(contrasts)} contrasts to {args.output_dir}")


if __name__ == "__main__":
    main()
