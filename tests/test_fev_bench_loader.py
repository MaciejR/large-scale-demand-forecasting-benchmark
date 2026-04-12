"""Tests for fev-bench data loader."""

import sys
sys.path.insert(0, "benchmark/code")

import pytest

from data.loaders.fev_bench import (
    RETAIL_TASKS,
    COVARIATE_TASKS,
    load_fev_bench_task,
)


def test_retail_tasks_count():
    """Should have 20 retail-domain tasks."""
    assert len(RETAIL_TASKS) == 20


def test_covariate_tasks_subset():
    """Covariate tasks should be a subset of retail tasks."""
    assert all(t in RETAIL_TASKS for t in COVARIATE_TASKS)


def test_known_tasks_present():
    """Spot-check key task names exist."""
    assert "m5_1D" in RETAIL_TASKS
    assert "favorita_stores_1D" in RETAIL_TASKS
    assert "rossmann_1D" in RETAIL_TASKS
    assert "rohlik_sales_1D" in RETAIL_TASKS


def _fev_available():
    try:
        import fev
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _fev_available(),
    reason="fev package not installed"
)
def test_load_returns_correct_columns():
    """Output must have series_id, ds, y at minimum."""
    df, metadata = load_fev_bench_task("hierarchical_sales_1D")
    assert "series_id" in df.columns
    assert "ds" in df.columns
    assert "y" in df.columns


@pytest.mark.skipif(
    not _fev_available(),
    reason="fev package not installed"
)
def test_load_with_covariates():
    """Covariate tasks should return extra columns."""
    df, metadata = load_fev_bench_task("m5_1D")
    assert "sell_price" in df.columns
    assert metadata["horizon"] == 28
