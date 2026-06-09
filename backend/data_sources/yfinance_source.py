"""Default DataSource backed by yfinance. TODO: implement (Eran)."""
from __future__ import annotations
import pandas as pd
from .base import DataSource

_INTERVAL_MAP = {"daily": "1d", "weekly": "1wk", "monthly": "1mo"}


class YFinanceSource(DataSource):
    def get_candles(self, ticker, interval, start, end=None) -> pd.DataFrame:
        # TODO: yfinance.download(ticker, interval=_INTERVAL_MAP[interval], start=start, end=end)
        raise NotImplementedError

    def get_last_close(self, ticker, interval) -> dict:
        # TODO: return last fully-closed candle as a dict
        raise NotImplementedError

    def is_available(self) -> bool:
        # TODO: lightweight ping / try/except around a tiny request
        raise NotImplementedError
