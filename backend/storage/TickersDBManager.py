from storage.TickerDB import TickerDB

class TickersDBManager:
    def __init__(self, db_name: str, tickers: list[str]):
        self.db_name = db_name
        self.tickers = tickers
        self.ticker_dbs = {ticker: TickerDB(db_name, ticker) for ticker in tickers}

    def get_ticker(self, ticker: str) -> TickerDB:
        if ticker not in self.ticker_dbs:
            raise ValueError(f"Unknown ticker '{ticker}'. Available: {list(self.ticker_dbs.keys())}")
        return self.ticker_dbs[ticker]

    def add_dataframe(self, ticker: str, df):
        self.get_ticker(ticker).add_dataframe(df)

    def get_data_as_pd(self, ticker: str, horizon: str, start_date: str = None):
        return self.get_ticker(ticker).get_data_as_pd(horizon, start_date)

    def get_data_as_eod(self, ticker: str, horizon: str, start_date: str = None):
        return self.get_ticker(ticker).get_data_as_eod(horizon, start_date)

    def get_latest_dates(self) -> dict:
        return {ticker: db.get_latest_date() for ticker, db in self.ticker_dbs.items()}

    def close(self):
        for db in self.ticker_dbs.values():
            db.close()



