"""
Cost tracking utilities for benchmark experiments.
Tracks runtime, estimates Azure cost, CO2 emissions, and throughput.
"""

import time


# Hardware specs: TDP in Watts, hourly cost in USD.
# Cloud entries price Azure `swedencentral` at time of writing.
# M_SERIES_MAC prices the *marginal electricity* of running inference on
# an M-series laptop the user already owns: ~30 W sustained draw ×
# Polish residential electricity ≈ $0.006/hr. This is the honest
# marginal cost from a retail-practitioner framing — it excludes capex
# amortization of the laptop itself, which is a sunk cost if the
# machine would exist anyway.
HARDWARE_SPECS = {
    "E4DS_V4": {"tdp_w": 65, "cost_per_hour": 0.38, "grid": "sweden"},
    "NC6": {"tdp_w": 150, "cost_per_hour": 0.90, "grid": "sweden"},
    "T4": {"tdp_w": 70, "cost_per_hour": 0.53, "grid": "sweden"},
    "K80": {"tdp_w": 150, "cost_per_hour": 0.90, "grid": "sweden"},
    "A100": {"tdp_w": 300, "cost_per_hour": 3.40, "grid": "sweden"},
    "M_SERIES_MAC": {"tdp_w": 30, "cost_per_hour": 0.006, "grid": "poland"},
}

# Grid carbon intensity (kg CO2 per kWh).
# Sweden: mostly hydro/nuclear (swedencentral 2025 baseline was 0.274
# under older accounting; 0.015 reflects the marginal-hydro assumption
# the paper uses in §5.1.2 and §5.2.3).
# Poland: coal-heavy residential grid (~0.65 kgCO2/kWh, 2025 baseline).
GRID_CO2_KG_PER_KWH = {
    "sweden": 0.015,
    "poland": 0.65,
}

# Back-compat alias for code that still imports the Sweden constant directly.
SWEDEN_GRID_CO2_KG_PER_KWH = GRID_CO2_KG_PER_KWH["sweden"]


class CostTracker:
    """Track compute cost, CO2, and throughput for an experiment run."""

    def __init__(self, hardware: str = "E4DS_V4"):
        if hardware not in HARDWARE_SPECS:
            raise ValueError(
                f"Unknown hardware '{hardware}'. Options: {list(HARDWARE_SPECS)}"
            )
        self.hardware = hardware
        self._start_time = None
        self._runtime_sec = None

    def start(self):
        """Mark experiment start."""
        self._start_time = time.time()

    def stop(self):
        """Mark experiment end."""
        self._runtime_sec = time.time() - self._start_time

    @property
    def runtime_sec(self) -> float:
        return self._runtime_sec or 0.0

    @property
    def runtime_hours(self) -> float:
        return self.runtime_sec / 3600.0

    @property
    def cost_usd(self) -> float:
        """Estimated Azure cost based on runtime and hardware hourly rate."""
        rate = HARDWARE_SPECS[self.hardware]["cost_per_hour"]
        return self.runtime_hours * rate

    @property
    def co2_kg(self) -> float:
        """Estimated CO2 emissions: TDP x runtime x grid carbon intensity."""
        spec = HARDWARE_SPECS[self.hardware]
        tdp_w = spec["tdp_w"]
        grid = spec.get("grid", "sweden")
        energy_kwh = (tdp_w / 1000.0) * self.runtime_hours
        return energy_kwh * GRID_CO2_KG_PER_KWH[grid]

    def series_per_second(self, n_series: int) -> float:
        """Inference throughput: series processed per second."""
        if self.runtime_sec <= 0:
            return 0.0
        return n_series / self.runtime_sec

    def to_dict(self, n_series: int = 0) -> dict:
        """Return all cost metrics as a flat dictionary for MLflow logging."""
        return {
            "runtime_sec": self.runtime_sec,
            "runtime_hours": self.runtime_hours,
            "cost_usd": self.cost_usd,
            "co2_kg": self.co2_kg,
            "series_per_second": self.series_per_second(n_series) if n_series else 0.0,
            "hardware": self.hardware,
        }
