"""
GPU detection and LightGBM device resolution.

LightGBM does not use CUDA the way PyTorch or XGBoost do. Its GPU build runs on
OpenCL via device="gpu", and that build is often absent from the standard pip wheel.
So instead of trusting a CUDA probe, we actually try to fit a tiny LightGBM model on
the GPU and fall back to the CPU if anything fails. The detection result is cached so
the probe runs at most once per process.
"""

from __future__ import annotations

import numpy as np

# Cache so the GPU probe runs only once per process.
_RESOLVED_DEVICE: str | None = None


def check_gpu() -> tuple[bool, str]:
    """
    Report whether a CUDA GPU is visible. This is informational only. The training
    code does not rely on it, because LightGBM uses OpenCL, not CUDA.

    Returns:
        (available, human_readable_info)
    """
    try:
        import torch  # optional, only used for a friendly device name

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            return True, f"CUDA GPU visible: {name} ({mem_gb:.1f} GB)"
    except Exception:
        pass
    return False, "No CUDA GPU reported by torch"


def resolve_lgbm_device() -> str:
    """
    Decide which device LightGBM should use by actually trying a tiny GPU fit.

    Returns:
        "gpu" if a GPU-enabled LightGBM trains successfully, otherwise "cpu".
    """
    global _RESOLVED_DEVICE
    if _RESOLVED_DEVICE is not None:
        return _RESOLVED_DEVICE

    try:
        import lightgbm as lgb

        # Two tiny rows are enough to force LightGBM to touch the device.
        x = np.array([[0.0, 1.0], [1.0, 0.0], [0.5, 0.5], [0.2, 0.8]])
        y = np.array([0.0, 1.0, 0.5, 0.7])
        probe = lgb.LGBMRegressor(
            objective="quantile",
            alpha=0.5,
            n_estimators=1,
            device="gpu",
            verbosity=-1,
        )
        probe.fit(x, y)
        _RESOLVED_DEVICE = "gpu"
        print("[gpu] LightGBM GPU (OpenCL) verified -- training will use the GPU")
    except Exception as exc:
        _RESOLVED_DEVICE = "cpu"
        print(f"[gpu] LightGBM GPU not available -- falling back to CPU ({type(exc).__name__})")

    return _RESOLVED_DEVICE
