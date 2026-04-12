"""
Cost tracking utilities for benchmark experiments.
Tracks runtime, estimates Azure cost, CO2 emissions, and throughput.
"""

import time


# Hardware specs: TDP in Watts, Azure hourly cost in USD
HARDWARE_SPECS = {
    "E4DS_V4": {"tdp_w": 65, "cost_per_hour": 0.38},
    "NC6": {"tdp_w": 150, "cost_per_hour": 0.90},
    "T4": {"tdp_w": 70, "cost_per_hour": 0.53},
    "K80": {"tdp_w": 150, "cost_per_hour": 0.90},
    "A100": {"tdp_w": 300, "cost_per_hour": 3.40},
}

# Sweden grid carbon intensity (kg CO2 per kWh) — mostly hydro/nuclear
SWEDEN_GRID_CO2_KG_PER_KWH = 0.015


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
        tdp_w = HARDWARE_SPECS[self.hardware]["tdp_w"]
        energy_kwh = (tdp_w / 1000.0) * self.runtime_hours
        return energy_kwh * SWEDEN_GRID_CO2_KG_PER_KWH

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
