import yfinance as yf
import pandas as pd
from  eod_data.Ticker_EOD_Extractor import Ticker_EOD_Extractor

class Tickers_EOD_Manager:
    def __init__(self, tickers_list, periods=[10, 50, 100, 150, 200]):
        self.tickers_list = tickers_list
        self.periods = periods

    def fetch_daily_tickers_data(self, tickers: list[str]) -> dict[str, pd.DataFrame]:
        raw_df = yf.download(tickers, start="2000-01-01", interval="1d", auto_adjust=False, progress=False)
        raw_df.index = raw_df.index.strftime("%Y-%m-%d")

        if len(tickers) == 1:
            raw_df.columns = raw_df.columns.get_level_values(0)
            return {tickers[0]: raw_df.dropna(subset=["Close"])}

        ticker_dfs = {}
        for ticker in tickers:
            ticker_df = raw_df.xs(ticker, axis=1, level=1)
            ticker_dfs[ticker] = ticker_df.dropna(subset=["Close"])

        return ticker_dfs

    def extract_all_tickers_data(self, trim_to_start_date: dict[str, str] = None) -> dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
        tickers_data = self.fetch_daily_tickers_data(self.tickers_list + ["^VIX"])
        all_data = {}
        for ticker in self.tickers_list:
            extractor = Ticker_EOD_Extractor(ticker, tickers_data[ticker], tickers_data["^VIX"], periods=self.periods)
            ticker_data = extractor.extract_ticker_data(trim_to_start_date[ticker]['db_latest'])
            ticker_data_daily, ticker_data_weekly, ticker_data_monthly = self.split_by_horizon(ticker_data)
            all_data[ticker] = ticker_data_daily, ticker_data_weekly, ticker_data_monthly
            
        return all_data
    
    def split_by_horizon(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        daily_cols   = [col for col in df.columns if "daily"   in col or "prev_day" in col]
        weekly_cols  = [col for col in df.columns if "weekly"  in col or "week" in col]
        monthly_cols = [col for col in df.columns if "monthly" in col or "month" in col]

        return df[daily_cols], df[weekly_cols], df[monthly_cols]