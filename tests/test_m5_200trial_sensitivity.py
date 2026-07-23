"""Tests for the M5 LightGBM 200-trial sensitivity artifact."""

from pathlib import Path
import shutil
import sys

import pandas as pd
import pytest

sys.path.insert(0, "analysis")

from source_b_m5_200trial_sensitivity import (  # noqa: E402
    build_sensitivity_tables,
    load_manifest,
    validate_artifact,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "m5_200trial" / "artifact_manifest.json"


def test_m5_200trial_manifest_validates_real_artifact():
    manifest = load_manifest(MANIFEST_PATH)
    run_dirs = validate_artifact(manifest, ROOT)

    assert [path.name for path in run_dirs] == manifest["expected_dirs"]
    assert "source_b_v1_15_strong_lightgbm_200trial_top_volume_100" not in {
        path.name for path in run_dirs
    }


def test_m5_200trial_complete_runs_have_200_trials():
    manifest = load_manifest(MANIFEST_PATH)
    run_root = ROOT / manifest["run_root"]
    for run_name in manifest["expected_dirs"]:
        trials = pd.read_csv(run_root / run_name / "lightgbm_tuning_trials.csv")
        assert len(trials) == 200
        assert trials["trial"].is_unique
        assert set(trials["dataset"].unique()) == {"M5"}


def test_m5_200trial_generator_writes_expected_chronos2_contrasts(tmp_path):
    outputs = build_sensitivity_tables(
        manifest_path=MANIFEST_PATH,
        root=ROOT,
        source_b_metrics_path=ROOT / "analysis" / "figures" / "source_b_paired_panel_per_series_metrics.csv",
        output_dir=tmp_path / "data",
        fig_dir=tmp_path / "figures",
        n_boot=100,
        seed=20260714,
    )

    contrasts = pd.read_csv(outputs["contrasts"])
    chronos2 = contrasts[contrasts["model_name"] == "chronos2"].sort_values("horizon")
    assert chronos2["horizon"].tolist() == [7, 14, 28]
    assert (chronos2["log_ratio"] < 0).all()
    assert (chronos2["ci95_high"] < 0).all()
    assert set(chronos2["baseline_model"]) == {"lightgbm_tuned_cov", "lightgbm_tuned_direct"}


def test_m5_200trial_validation_rejects_partial_run(tmp_path):
    manifest = load_manifest(MANIFEST_PATH)
    run_root = tmp_path / manifest["run_root"]
    run_root.mkdir(parents=True)
    real_root = ROOT / manifest["run_root"]
    for run_name in manifest["expected_dirs"]:
        shutil.copytree(real_root / run_name, run_root / run_name)
    partial = run_root / manifest["excluded_dirs"][0]
    partial.mkdir()
    (partial / "lightgbm_tuning_trials_incremental.csv").write_text("trial,value\n0,1.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Excluded partial run directory"):
        validate_artifact(manifest, tmp_path)
