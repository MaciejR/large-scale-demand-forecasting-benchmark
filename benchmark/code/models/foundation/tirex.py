"""
TiRex (NX-AI) zero-shot forecaster for the local sensitivity run.

Reference: A13 (ARES 2025) — TiRex is an xLSTM-based time-series
foundation model. ~35 M parameters. Published MPS-compatible inference
in the reference implementation, though the custom xLSTM kernels have
CUDA-first support and fall back to a pure-PyTorch slow path on MPS.
This means TiRex inference is slower on a MacBook than Chronos-Bolt-
Tiny or TabPFN-TS but still feasible inside the §5.4.3 budget.

Requires: pip install "tirex-ts>=0.3"  (import path: `from tirex import load_model`)

Device note: on MPS, expect ~5-15x slowdown relative to CUDA per the
TiRex GitHub benchmarks. We document the effect in the §5.4.6
cross-protocol comparison table (our LOCAL row will be slower than
A13's published throughput, which is expected).
"""

import numpy as np
import pandas as pd


class TiRexForecaster:
    """Wrapper for TiRex zero-shot point forecasting."""

    def __init__(
        self,
        model_id: str = "NX-AI/TiRex",
        device: str = "mps",
    ):
        self.model_id = model_id
        self.device = device
        self._model = None

    def _load_model(self):
        if self._model is None:
            from tirex import load_model

            try:
                self._model = load_model(self.model_id, device=self.device)
            except (RuntimeError, NotImplementedError) as err:
                if self.device == "mps":
                    print(
                        f"WARNING: TiRex MPS load failed ({err}); "
                        f"falling back to CPU. Expect 30-60s/series on "
                        f"a MacBook for h=28 — use a smaller dataset "
                        f"for the initial dry run if this is slow."
                    )
                    self.device = "cpu"
                    self._model = load_model(self.model_id, device="cpu")
                else:
                    raise

    def predict(self, train: pd.Series, horizon: int) -> pd.Series:
        """Zero-shot point forecast (TiRex deterministic decoder output)."""
        import torch

        self._load_model()
        context = torch.tensor(train.values, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            out = self._model.forecast(context, prediction_length=horizon)

        if isinstance(out, dict):
            point = out.get("mean", out.get("median", out.get("predictions")))
        else:
            point = out
        if hasattr(point, "cpu"):
            point = point.cpu()
        arr = np.asarray(point).reshape(-1)[:horizon]
        return pd.Series(arr)
