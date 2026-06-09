"""Resolve the right model artifact for a given (index, horizon).

Default policy: one model per (index x horizon). Built so it can be collapsed later
(per-horizon, or one global model) without touching callers. See ai/README.md.
"""
from __future__ import annotations


def artifact_path(index: str, horizon: str) -> str:
    return f"ai/artifacts/{index}_{horizon}.model"


def get_model(index: str, horizon: str):
    """Load (or lazily create) the model for this (index, horizon)."""
    raise NotImplementedError
