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

import os

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
        # Override: when MPS loads successfully but the xLSTM fallback
        # dispatches one element at a time through MPSGraph, a single
        # forecast window takes tens of seconds and the sweep stalls.
        # Empirically the CPU path is 5-10x faster for the same cell.
        # TIREX_FORCE_CPU=1 short-circuits the MPS attempt.
        if os.environ.get("TIREX_FORCE_CPU", "") == "1":
            device = "cpu"
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

        if isinstance(out, tuple):
            mean = out[1]
        elif isinstance(out, dict):
            mean = out.get("mean", out.get("median", out.get("predictions")))
        else:
            mean = out
        if hasattr(mean, "cpu"):
            mean = mean.cpu()
        arr = np.asarray(mean).reshape(-1)[:horizon]
        return pd.Series(arr)

    def predict_batch(
        self,
        histories,
        horizon: int,
        quantile_levels: list[float] | None = None,
    ) -> np.ndarray:
        """
        Batched zero-shot point forecast.

        TiRex accepts a 2D context tensor with shape ``(batch, context)``.
        When histories have ragged starts, they are grouped by equal context
        length so the model sees the same history each series would receive
        in the scalar path, without leading zero or NaN padding.
        """
        import torch

        self._load_model()
        arrays = [np.asarray(hist, dtype=np.float32) for hist in histories]
        if not arrays:
            return np.empty((0, horizon), dtype=np.float32)

        forecasts = np.empty((len(arrays), horizon), dtype=np.float32)
        by_length: dict[int, list[int]] = {}
        for idx, arr in enumerate(arrays):
            by_length.setdefault(len(arr), []).append(idx)

        for indices in by_length.values():
            context = torch.tensor(
                np.stack([arrays[idx] for idx in indices]),
                dtype=torch.float32,
            )

            with torch.no_grad():
                out = self._model.forecast(context, prediction_length=horizon)

            if isinstance(out, tuple):
                mean = out[1]
            elif isinstance(out, dict):
                mean = out.get("mean", out.get("median", out.get("predictions")))
            else:
                mean = out
            if hasattr(mean, "cpu"):
                mean = mean.cpu()
            arr = np.asarray(mean, dtype=np.float32)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            forecasts[indices, :] = arr[:, :horizon]

        return forecasts
