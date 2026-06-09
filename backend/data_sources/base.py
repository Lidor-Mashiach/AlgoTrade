"""Abstract data-source interface so yfinance and scraping are interchangeable."""
from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd


class DataSource(ABC):
    """Contract every data source (yfinance / scraper) must satisfy."""

    @abstractmethod
    def get_candles(self, ticker: str, interval: str,
                    start: str, end: str | None = None) -> pd.DataFrame:
        """Return an OHLCV DataFrame. interval in {daily, weekly, monthly}."""

    @abstractmethod
    def get_last_close(self, ticker: str, interval: str) -> dict:
        """Return the last *closed* candle: {date, open, high, low, close, volume}."""

    @abstractmethod
    def is_available(self) -> bool:
        """Connectivity check used for graceful offline handling."""
