"""Tests for GIFT-Eval data loader."""

import sys
sys.path.insert(0, "benchmark/code")

import pytest

from data.loaders.gift_eval import SALES_DATASETS, load_gift_eval


def _gift_eval_available():
    try:
        import gift_eval
        return True
    except ImportError:
        return False


def test_sales_datasets_list():
    """Should expose the 4 sales domain configs."""
    assert "car_parts_with_missing" in SALES_DATASETS
    assert "restaurant" in SALES_DATASETS
    assert "hierarchical_sales/D" in SALES_DATASETS
    assert "hierarchical_sales/W" in SALES_DATASETS
    assert len(SALES_DATASETS) == 4


@pytest.mark.skipif(
    not _gift_eval_available(),
    reason="gift_eval package or data not available"
)
def test_load_returns_correct_columns():
    """Output must have exactly [series_id, ds, y]."""
    df = load_gift_eval("restaurant", term="short")
    assert list(df.columns) == ["series_id", "ds", "y"]


@pytest.mark.skipif(
    not _gift_eval_available(),
    reason="gift_eval package or data not available"
)
def test_load_types():
    """Column types: series_id=str, ds=datetime, y=float."""
    df = load_gift_eval("restaurant", term="short")
    assert df["ds"].dtype == "datetime64[ns]"
    assert df["y"].dtype == float
