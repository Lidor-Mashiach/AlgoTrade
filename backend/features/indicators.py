"""Technical indicator helpers (SMA, EMA, RSI, Bollinger). Pure functions over price series."""
from __future__ import annotations
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index. TODO: verify against a reference implementation."""
    raise NotImplementedError


def bollinger(series: pd.Series, window: int = 20, num_std: float = 2.0):
    """Return (upper_band, lower_band)."""
    raise NotImplementedError
