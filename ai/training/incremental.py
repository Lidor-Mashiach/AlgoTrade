"""Incremental update: absorb the candles the backend reported as missed.

Strategy (see ai/README.md): warm-start / partial_fit on a rolling window so we never
retrain from scratch and disk usage stays bounded.
"""
from __future__ import annotations


def update(index: str, horizon: str, missed: int, cfg: dict) -> None:
    """
    missed = number of newly-closed candles for this horizon (from sync_manager).
    If missed == 0 -> no-op (skip straight to inference).
    TODO: load model, build the recent window, model.partial_fit(...), save.
    """
    if missed == 0:
        return
    raise NotImplementedError
