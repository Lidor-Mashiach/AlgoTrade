"""
Inference predictor.

The runtime entry point the backend and CLI call to turn a feature row into a band and a
confidence. Models are loaded lazily from artifacts/ and cached, so the first call for a
horizon pays the load cost and later calls are fast.

The public contract is intentionally stable:

    predict(ticker: str, horizon: str, features: dict) -> {
        "low": Q10, "mid": Q50, "high": Q90, "confidence": float in [0, 1]
    }

low and high are the band edges in percent points, mid is the median, and confidence is
a heuristic that rises as the band tightens. The recommendation mapping (Long, Short,
Stay-out) is applied downstream by the backend or CLI, not here.
"""

from __future__ import annotations

# --- make the ai/ root importable regardless of where this script is launched from ---
import sys
import pathlib

for _parent in pathlib.Path(__file__).resolve().parents:
    if (_parent / "config.py").exists() and (_parent / "utils").is_dir():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break

import json

import numpy as np
import pandas as pd

import config

# ----------------------------------------------------------------------------------
# GLOBAL PARAMETERS
# ----------------------------------------------------------------------------------
# Reference band width (percent points) mapped to zero confidence. A band of zero width
# maps to confidence 1. Tune to taste once real bands are observed.
CONFIDENCE_REF_WIDTH = 10.0

_CACHE: dict[str, dict] = {}   # horizon -> {"boosters": {...}, "features": [...]}


def _load_horizon(horizon: str) -> dict:
    """Load and cache the three boosters and the feature order for one horizon."""
    if horizon in _CACHE:
        return _CACHE[horizon]

    import lightgbm as lgb

    meta_path = config.inference_metadata_path(horizon)
    if not meta_path.exists():
        raise FileNotFoundError(
            f"No inference models for horizon '{horizon}' at {meta_path.parent}. "
            f"Run 3_Production-FinalTraining/build_final_models.py first."
        )
    metadata = json.loads(meta_path.read_text())

    boosters = {}
    for qname in config.QUANTILES:
        boosters[qname] = lgb.Booster(model_file=str(config.inference_model_path(horizon, qname)))

    entry = {"boosters": boosters, "features": metadata["feature_columns"]}
    _CACHE[horizon] = entry
    return entry


def _confidence(width: float) -> float:
    """Map band width to a confidence in [0, 1]. Tighter band means higher confidence."""
    return float(np.clip(1.0 - width / CONFIDENCE_REF_WIDTH, 0.0, 1.0))


def predict(ticker: str, horizon: str, features: dict) -> dict:
    """
    Predict the band for one ticker and horizon from a feature dictionary.

    Unknown feature keys are ignored and missing model features are left as NaN, which
    LightGBM handles natively. The band edges are sorted so low never exceeds high.
    """
    if horizon not in config.HORIZONS:
        raise ValueError(f"Unknown horizon '{horizon}'. Expected one of {config.HORIZONS}.")

    entry = _load_horizon(horizon)
    feature_cols = entry["features"]

    # Build a one-row frame in the exact training feature order.
    row = {col: features.get(col, np.nan) for col in feature_cols}
    if "ticker" in feature_cols:
        row["ticker"] = ticker
    X = pd.DataFrame([row], columns=feature_cols)
    if "ticker" in X.columns:
        X["ticker"] = pd.Categorical(X["ticker"], categories=config.TICKERS)

    q_low = float(entry["boosters"]["q10"].predict(X)[0])
    q_mid = float(entry["boosters"]["q50"].predict(X)[0])
    q_high = float(entry["boosters"]["q90"].predict(X)[0])

    # Quantile crossing can happen on rare rows. Sort the edges to keep a valid band.
    low, high = sorted((q_low, q_high))
    return {
        "low": low,
        "mid": q_mid,
        "high": high,
        "confidence": _confidence(high - low),
    }
