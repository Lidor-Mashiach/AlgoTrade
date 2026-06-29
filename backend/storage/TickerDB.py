import sqlite3
import pandas as pd

from eod_data.Ticker_EOD import Ticker_EOD

class TickerDB:
    DAILY_COLS = [
        "close_daily_last", "pct_change_daily_last",
        "sma_daily_10", "sma_daily_50", "sma_daily_100", "sma_daily_150", "sma_daily_200",
        "ema_daily_10", "ema_daily_50", "ema_daily_100", "ema_daily_150", "ema_daily_200",
        "volume_prev_day", "volume_avg_daily_90",
        "low_prev_day", "high_prev_day",
        "bb_base_daily", "bb_upper_daily", "bb_lower_daily",
        "rsi_daily", "rsi_ma_daily", "rsi_gap_daily",
        "vix_daily_last",
    ]

    WEEKLY_COLS = [
        "close_weekly_last", "pct_change_week_current", "pct_change_week_prev",
        "sma_weekly_10", "sma_weekly_50", "sma_weekly_100", "sma_weekly_150", "sma_weekly_200",
        "ema_weekly_10", "ema_weekly_50", "ema_weekly_100", "ema_weekly_150", "ema_weekly_200",
        "volume_week_current", "volume_week_prev",
        "low_week_current", "high_week_current", "low_week_prev", "high_week_prev",
        "bb_base_weekly", "bb_upper_weekly", "bb_lower_weekly",
        "rsi_weekly", "rsi_ma_weekly", "rsi_gap_weekly",
        "vix_weekly_last",
    ]

    MONTHLY_COLS = [
        "close_monthly_last", "pct_change_month_current", "pct_change_month_prev",
        "sma_monthly_10", "sma_monthly_50", "sma_monthly_100", "sma_monthly_150", "sma_monthly_200",
        "ema_monthly_10", "ema_monthly_50", "ema_monthly_100", "ema_monthly_150", "ema_monthly_200",
        "volume_month_current", "volume_month_prev",
        "low_month_current", "high_month_current", "low_month_prev", "high_month_prev",
        "bb_base_monthly", "bb_upper_monthly", "bb_lower_monthly",
        "rsi_monthly", "rsi_ma_monthly", "rsi_gap_monthly",
        "vix_monthly_last",
    ]

    def __init__(self, db_name: str, ticker: str):
        self.db_name = db_name
        self.ticker = ticker
        safe_ticker = ticker.replace(".", "_").replace("^", "")
        self.daily_table = f"{safe_ticker}_daily"
        self.weekly_table = f"{safe_ticker}_weekly"
        self.monthly_table = f"{safe_ticker}_monthly"
        self.connection = sqlite3.connect(db_name)
        self.init_tables()

    def init_tables(self):
        cursor = self.connection.cursor()
        for table, cols in [
            (self.daily_table,   self.DAILY_COLS),
            (self.weekly_table,  self.WEEKLY_COLS),
            (self.monthly_table, self.MONTHLY_COLS),
        ]:
            col_definitions = ", ".join(f"{col} REAL" for col in cols)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    date TEXT PRIMARY KEY,
                    {col_definitions}
                )
            """)
        self.connection.commit()

    def get_data_as_pd(self, horizon: str, start_date: str = None) -> pd.DataFrame:
        tables = {
            "daily":   self.daily_table,
            "weekly":  self.weekly_table,
            "monthly": self.monthly_table,
        }
        if horizon not in tables:
            raise ValueError(f"Unknown horizon '{horizon}'. Use 'daily', 'weekly', or 'monthly'.")

        query = f"SELECT * FROM {tables[horizon]}"
        params = []
        if start_date:
            query += " WHERE date >= ?"
            params.append(start_date)
        query += " ORDER BY date"
        return pd.read_sql_query(query, self.connection, params=params, index_col="date")
    
    def get_data_as_eod(self, horizon: str, start_date: str = None) -> list[Ticker_EOD]:
        df = self.get_data_as_pd(horizon, start_date)
        return [Ticker_EOD(ticker=self.ticker, date=str(date), features=row.to_dict()) for date, row in df.iterrows()]

    def add_row(self, date: str, features: dict, auto_commit: bool = True):
        cursor = self.connection.cursor()
        for table, cols in [
            (self.daily_table, self.DAILY_COLS),
            (self.weekly_table, self.WEEKLY_COLS),
            (self.monthly_table, self.MONTHLY_COLS),
        ]:
            row = {col: features.get(col) for col in cols}
            placeholders = ", ".join("?" * len(cols))
            col_names = ", ".join(cols)
            cursor.execute(f"""
                INSERT OR REPLACE INTO {table} (date, {col_names})
                VALUES (?, {placeholders})
            """, [date] + list(row.values()))
        if auto_commit:
            self.connection.commit()

    def add_dataframe(self, df: pd.DataFrame):
        for table, cols in [
            (self.daily_table, self.DAILY_COLS),
            (self.weekly_table, self.WEEKLY_COLS),
            (self.monthly_table, self.MONTHLY_COLS),
        ]:
            try:
                available_cols = [col for col in cols if col in df.columns]
                df[available_cols].to_sql(table, self.connection, if_exists="replace", index=True, index_label="date")
            except Exception as e:
                print(f"Failed to insert into {table} for ticker {self.ticker}: {e}")
                raise

    def get_latest_date(self) -> dict:
        cursor = self.connection.cursor()
        latest_dates = {}
        for horizon, table in [
            ("daily",   self.daily_table),
            ("weekly",  self.weekly_table),
            ("monthly", self.monthly_table),
        ]:
            cursor.execute(f"SELECT MAX(date) FROM {table}")
            latest_dates[horizon] = cursor.fetchone()[0]
        return latest_dates

    def close(self):
        self.connection.close()