import yfinance as yf
from storage.TickersDBManager import TickersDBManager

class SyncManager:
    def __init__(self, tickers: list[str], ticker_db_manager: TickersDBManager):
        self.tickers = tickers
        self.ticker_db_manager = ticker_db_manager

    def get_sync_status(self) -> dict:
        sync_status = {}
        for ticker in self.tickers:
            yf_latest = self.get_yf_latest_date(ticker)
            db_latest_daily = self.ticker_db_manager.get_ticker(ticker).get_latest_date()["daily"]

            sync_status[ticker] = {
                "yf_latest": yf_latest,
                "db_latest": db_latest_daily,
                "is_synced": self.is_synced(yf_latest, db_latest_daily)
            }

        return sync_status
    
    def get_yf_latest_date(self, ticker: str) -> str:
        df = yf.Ticker(ticker).history(period="1d", interval="1m")
        if df.empty:
            return None
        return df.index.max().strftime("%Y-%m-%d")
    
    def is_synced(self, yf_latest: str, db_latest: str) -> bool:
        if yf_latest is None or db_latest is None:
            return False
        return yf_latest[:10] == db_latest[:10]