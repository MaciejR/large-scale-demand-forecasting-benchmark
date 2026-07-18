"""Tests for Source B paired-panel aggregation."""

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "analysis")

from source_b_paired_panel_report import compute_fm_contrasts_with_covariance


def test_shared_bootstrap_covariance_matrix_is_symmetric():
    summary = pd.DataFrame(
        [
            {"dataset": "D", "horizon": 7, "model_name": "lightgbm_cov", "WAPE_aggregate": 0.20},
            {"dataset": "D", "horizon": 7, "model_name": "fm_a", "WAPE_aggregate": 0.10},
            {"dataset": "D", "horizon": 7, "model_name": "fm_b", "WAPE_aggregate": 0.15},
        ]
    )
    metrics = pd.DataFrame(
        [
            {"dataset": "D", "horizon": 7, "model_name": model, "series_id": sid, "abs_error": err, "abs_y": 10.0}
            for sid, base_err, fm_a_err, fm_b_err in [
                ("s1", 2.0, 1.0, 1.4),
                ("s2", 3.0, 1.2, 2.2),
                ("s3", 1.0, 0.7, 0.8),
                ("s4", 4.0, 1.5, 2.8),
            ]
            for model, err in [
                ("lightgbm_cov", base_err),
                ("fm_a", fm_a_err),
                ("fm_b", fm_b_err),
            ]
        ]
    )

    contrasts, draws, cov, cov_long = compute_fm_contrasts_with_covariance(
        summary,
        metrics,
        n_boot=200,
        seed=123,
    )

    assert len(contrasts) == 2
    assert draws.shape == (2, 201)
    matrix = cov.set_index("contrast_id")
    values = matrix.to_numpy(float)
    assert values.shape == (2, 2)
    assert np.allclose(values, values.T)
    assert np.all(np.diag(values) > 0)
    assert len(cov_long) == 4

    fm_a = contrasts[contrasts["model_name"] == "fm_a"].iloc[0]
    expected = np.log((1.0 + 1.2 + 0.7 + 1.5) / (2.0 + 3.0 + 1.0 + 4.0))
    assert fm_a["baseline_model"] == "lightgbm_cov"
    assert fm_a["log_ratio"] == expected


def test_shared_bootstrap_is_independent_of_input_row_order():
    summary_rows = []
    metric_rows = []
    for dataset, offset in [("A", 0.0), ("B", 0.5)]:
        summary_rows.extend(
            [
                {
                    "dataset": dataset,
                    "horizon": 7,
                    "model_name": "lightgbm_cov",
                    "WAPE_aggregate": 0.20 + offset,
                },
                {
                    "dataset": dataset,
                    "horizon": 7,
                    "model_name": "fm_a",
                    "WAPE_aggregate": 0.10 + offset,
                },
                {
                    "dataset": dataset,
                    "horizon": 14,
                    "model_name": "lightgbm_cov",
                    "WAPE_aggregate": 0.30 + offset,
                },
                {
                    "dataset": dataset,
                    "horizon": 14,
                    "model_name": "fm_a",
                    "WAPE_aggregate": 0.15 + offset,
                },
            ]
        )
        for horizon, multiplier in [(7, 1.0), (14, 1.2)]:
            for sid, base_err, fm_err in [
                ("s1", 2.0 + offset, 1.0 + offset),
                ("s2", 3.0 + offset, 1.4 + offset),
                ("s3", 1.0 + offset, 0.8 + offset),
                ("s4", 4.0 + offset, 1.9 + offset),
            ]:
                metric_rows.extend(
                    [
                        {
                            "dataset": dataset,
                            "horizon": horizon,
                            "model_name": "lightgbm_cov",
                            "series_id": sid,
                            "abs_error": base_err * multiplier,
                            "abs_y": 10.0,
                        },
                        {
                            "dataset": dataset,
                            "horizon": horizon,
                            "model_name": "fm_a",
                            "series_id": sid,
                            "abs_error": fm_err * multiplier,
                            "abs_y": 10.0,
                        },
                    ]
                )

    summary = pd.DataFrame(summary_rows)
    metrics = pd.DataFrame(metric_rows)
    reversed_summary = summary.iloc[::-1].reset_index(drop=True)
    reversed_metrics = metrics.iloc[::-1].reset_index(drop=True)

    expected = compute_fm_contrasts_with_covariance(
        summary,
        metrics,
        n_boot=50,
        seed=456,
    )
    actual = compute_fm_contrasts_with_covariance(
        reversed_summary,
        reversed_metrics,
        n_boot=50,
        seed=456,
    )

    for expected_frame, actual_frame in zip(expected, actual):
        pd.testing.assert_frame_equal(expected_frame, actual_frame)
