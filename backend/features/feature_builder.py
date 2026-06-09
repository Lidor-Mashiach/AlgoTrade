"""Assemble the full feature vector defined in backend/FEATURES.md for a given (index, horizon)."""
from __future__ import annotations
from ..data_sources.base import DataSource


def build_features(source: DataSource, ticker: str, horizon: str, cfg: dict) -> dict:
    """
    Produce every feature listed in FEATURES.md:
    price/returns, SMA/EMA, volume, range, Bollinger, RSI, VIX.
    Returns a flat {feature_key: value} dict ready for the AI module.
    TODO: implement using indicators.py + the data source.
    """
    raise NotImplementedError
