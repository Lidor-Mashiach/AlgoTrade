"""Alternative DataSource via scraping. Implement only if Eran picks scraping over API."""
from __future__ import annotations
from .base import DataSource


class ScraperSource(DataSource):
    def get_candles(self, ticker, interval, start, end=None):
        raise NotImplementedError("Scraping source — implement if chosen over the API.")

    def get_last_close(self, ticker, interval):
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError
