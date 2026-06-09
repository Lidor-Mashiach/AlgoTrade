"""Build train/validation/test sets from the backend feature table.

IMPORTANT: time-series data -> use chronological splits (no shuffling / no leakage).
"""
from __future__ import annotations


def build_dataset(index: str, horizon: str, cfg: dict):
    """
    Returns (X_train, y_train, X_val, y_val, X_test, y_test).
    Targets = % move of the NEXT candle close vs the last closed candle.
    TODO: implement; respect chronological ordering.
    """
    raise NotImplementedError
