"""Inference: turn a feature vector into a forecast range + confidence."""
from __future__ import annotations
from ..models.registry import get_model


def predict(index: str, horizon: str, features: dict) -> dict:
    """
    Returns {"low": float, "high": float, "confidence": float}.
    Range can come from mean +/- k*sigma or from quantile heads (see ai/README.md).
    """
    # model = get_model(index, horizon); return model.predict(features)
    raise NotImplementedError
