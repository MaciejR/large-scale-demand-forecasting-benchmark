"""Tests for cost tracking utilities."""

import time

import pytest

import sys
sys.path.insert(0, "benchmark/code")

from evaluation.cost import CostTracker


def test_tracker_measures_runtime():
    """CostTracker should measure elapsed wall-clock time."""
    tracker = CostTracker(hardware="E4DS_V4")
    tracker.start()
    time.sleep(0.1)
    tracker.stop()
    assert tracker.runtime_sec >= 0.09
    assert tracker.runtime_sec < 1.0


def test_co2_estimate_cpu():
    """CO2 estimate for CPU hardware uses correct TDP."""
    tracker = CostTracker(hardware="E4DS_V4")
    tracker.start()
    time.sleep(0.01)
    tracker.stop()
    co2 = tracker.co2_kg
    assert co2 >= 0
    assert isinstance(co2, float)


def test_co2_estimate_gpu():
    """CO2 estimate for GPU uses higher TDP."""
    tracker = CostTracker(hardware="T4")
    tracker._runtime_sec = 3600.0  # 1 hour
    co2 = tracker.co2_kg
    # T4 TDP=70W, 1h, Sweden grid=0.015 kg/kWh -> 0.07 * 0.015 = 0.00105
    assert 0.0005 < co2 < 0.01


def test_cost_usd_estimate():
    """Cost should be runtime x hourly rate."""
    tracker = CostTracker(hardware="T4")
    tracker._runtime_sec = 3600.0  # 1 hour
    # T4 NC4as ~$0.53/h
    assert 0.4 < tracker.cost_usd < 0.7


def test_series_per_second():
    """Throughput calculation."""
    tracker = CostTracker(hardware="E4DS_V4")
    tracker._runtime_sec = 10.0
    throughput = tracker.series_per_second(n_series=1000)
    assert throughput == 100.0


def test_to_dict():
    """Metrics dict should contain all expected keys."""
    tracker = CostTracker(hardware="E4DS_V4")
    tracker._runtime_sec = 60.0
    d = tracker.to_dict(n_series=500)
    assert "runtime_sec" in d
    assert "cost_usd" in d
    assert "co2_kg" in d
    assert "series_per_second" in d
    assert "hardware" in d
