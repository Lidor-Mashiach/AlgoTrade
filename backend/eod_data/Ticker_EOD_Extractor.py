import pandas as pd

class Ticker_EOD_Extractor:
    def __init__(self, ticker, ticker_daily_data, vix_daily_data, periods=[10, 50, 100, 150, 200]):
        self.ticker = ticker

        self.ticker_daily_data = ticker_daily_data.loc[:ticker_daily_data["Close"].last_valid_index()]

        self.vix_daily_data = vix_daily_data
        self.periods = periods

    def extract_ticker_data(self, start_date=None) -> pd.DataFrame:
        feature_blocks = [
            self.get_ticker_price_and_returns(self.ticker_daily_data),
            self.get_sma_features(self.ticker_daily_data),
            self.get_ema_features(self.ticker_daily_data),
            self.get_volume_features(self.ticker_daily_data),
            self.get_range_features(self.ticker_daily_data),
            self.get_bollinger_features(self.ticker_daily_data),
            self.get_rsi_features(self.ticker_daily_data),
            self.get_vix_features(self.ticker_daily_data, vix_daily=self.vix_daily_data),
        ]

        features_df = pd.concat(feature_blocks, axis=1)
        trimmed_df = self.trim_to_start_date(features_df, start_date)
        return trimmed_df

    def _add_time_group_columns(self, daily_data):
        df = daily_data.copy()
        datetime_index = pd.to_datetime(df.index)
        iso = datetime_index.isocalendar()
        week_id = iso["year"].astype(str) + "-" + iso["week"].astype(str).str.zfill(2)
        df["week_id"] = week_id.to_numpy()
        df["month_id"] = datetime_index.strftime("%Y-%m")
        return df

    def get_ticker_price_and_returns(self, daily_data) -> pd.DataFrame:
        df = self._add_time_group_columns(daily_data)

        weekly_close_by_week = df.groupby("week_id", sort=True).agg(weekly_close=("Close", "last"))
        monthly_close_by_month = df.groupby("month_id", sort=True).agg(monthly_close=("Close", "last"))

        current_week_open = df.groupby("week_id", sort=False)["Open"].transform("first")
        current_month_open = df.groupby("month_id", sort=False)["Open"].transform("first")

        out = pd.DataFrame(index=df.index)

        out["close_daily_last"] = df["Close"]
        out["pct_change_daily_last"] = df["Close"].pct_change(fill_method=None) * 100

        out["close_weekly_last"] = df["week_id"].map(weekly_close_by_week["weekly_close"].shift(1))
        out["pct_change_week_current"] = (df["Close"] - current_week_open) / current_week_open * 100
        out["pct_change_week_prev"] = df["week_id"].map(weekly_close_by_week["weekly_close"].pct_change().shift(1) * 100)

        out["close_monthly_last"] = df["month_id"].map(monthly_close_by_month["monthly_close"].shift(1))
        out["pct_change_month_current"] = (df["Close"] - current_month_open) / current_month_open * 100
        out["pct_change_month_prev"] = df["month_id"].map(monthly_close_by_month["monthly_close"].pct_change().shift(1) * 100)

        return out

    def get_sma_features(self, daily_data) -> pd.DataFrame:
        df = self._add_time_group_columns(daily_data)

        weekly_close_by_week = df.groupby("week_id", sort=True)["Close"].last()
        monthly_close_by_month = df.groupby("month_id", sort=True)["Close"].last()

        out = pd.DataFrame(index=df.index)

        for period in self.periods:
            closed_weekly_rolling_sum = weekly_close_by_week.rolling(period - 1).sum().shift(1)
            closed_monthly_rolling_sum = monthly_close_by_month.rolling(period - 1).sum().shift(1)

            out[f"sma_daily_{period}"] = df["Close"].rolling(period).mean()
            out[f"sma_weekly_{period}"] = (df["week_id"].map(closed_weekly_rolling_sum) + df["Close"]) / period
            out[f"sma_monthly_{period}"] = (df["month_id"].map(closed_monthly_rolling_sum) + df["Close"]) / period

        return out

    def get_ema_features(self, daily_data) -> pd.DataFrame:
        df = self._add_time_group_columns(daily_data)

        weekly_close_by_week = df.groupby("week_id", sort=True)["Close"].last()
        monthly_close_by_month = df.groupby("month_id", sort=True)["Close"].last()

        out = pd.DataFrame(index=df.index)

        for period in self.periods:
            smoothing_factor = 2 / (period + 1)

            last_closed_weekly_ema = weekly_close_by_week.ewm(span=period, adjust=False).mean().shift(1)
            last_closed_monthly_ema = monthly_close_by_month.ewm(span=period, adjust=False).mean().shift(1)

            out[f"ema_daily_{period}"] = df["Close"].ewm(span=period, adjust=False).mean()
            out[f"ema_weekly_{period}"] = smoothing_factor * df["Close"] + (1 - smoothing_factor) * df["week_id"].map(last_closed_weekly_ema)
            out[f"ema_monthly_{period}"] = smoothing_factor * df["Close"] + (1 - smoothing_factor) * df["month_id"].map(last_closed_monthly_ema)

        return out

    def get_volume_features(self, daily_data) -> pd.DataFrame:
        df = self._add_time_group_columns(daily_data)

        total_volume_by_week = df.groupby("week_id", sort=True)["Volume"].sum()
        total_volume_by_month = df.groupby("month_id", sort=True)["Volume"].sum()

        out = pd.DataFrame(index=df.index)

        out["volume_prev_day"] = df["Volume"].shift(1)
        out["volume_avg_daily_90"] = df["Volume"].rolling(90).mean()

        out["volume_week_current"] = df.groupby("week_id")["Volume"].cumsum()
        out["volume_week_prev"] = df["week_id"].map(total_volume_by_week.shift(1))

        out["volume_month_current"] = df.groupby("month_id")["Volume"].cumsum()
        out["volume_month_prev"] = df["month_id"].map(total_volume_by_month.shift(1))

        return out

    def get_range_features(self, daily_data) -> pd.DataFrame:
        df = self._add_time_group_columns(daily_data)

        weekly_low_by_week = df.groupby("week_id", sort=True)["Low"].min()
        weekly_high_by_week = df.groupby("week_id", sort=True)["High"].max()
        monthly_low_by_month = df.groupby("month_id", sort=True)["Low"].min()
        monthly_high_by_month = df.groupby("month_id", sort=True)["High"].max()

        out = pd.DataFrame(index=df.index)

        out["low_prev_day"] = df["Low"].shift(1)
        out["high_prev_day"] = df["High"].shift(1)

        out["low_week_current"] = df.groupby("week_id")["Low"].cummin()
        out["high_week_current"] = df.groupby("week_id")["High"].cummax()
        out["low_week_prev"] = df["week_id"].map(weekly_low_by_week.shift(1))
        out["high_week_prev"] = df["week_id"].map(weekly_high_by_week.shift(1))

        out["low_month_current"] = df.groupby("month_id")["Low"].cummin()
        out["high_month_current"] = df.groupby("month_id")["High"].cummax()
        out["low_month_prev"] = df["month_id"].map(monthly_low_by_month.shift(1))
        out["high_month_prev"] = df["month_id"].map(monthly_high_by_month.shift(1))

        return out

    def get_bollinger_features(self, daily_data) -> pd.DataFrame:
        bollinger_period = 20
        num_std_deviations = 2

        df = self._add_time_group_columns(daily_data)

        weekly_close_by_week = df.groupby("week_id", sort=True)["Close"].last()
        monthly_close_by_month = df.groupby("month_id", sort=True)["Close"].last()

        out = pd.DataFrame(index=df.index)

        daily_basis = df["Close"].rolling(bollinger_period).mean()
        daily_std = df["Close"].rolling(bollinger_period).std(ddof=0)
        out["bb_base_daily"] = daily_basis
        out["bb_upper_daily"] = daily_basis + num_std_deviations * daily_std
        out["bb_lower_daily"] = daily_basis - num_std_deviations * daily_std

        for horizon, close_by_period, group_col in [
            ("weekly", weekly_close_by_week, "week_id"),
            ("monthly", monthly_close_by_month, "month_id"),
        ]:
            closed_sum = close_by_period.rolling(bollinger_period - 1).sum().shift(1)
            closed_sum_squared = (close_by_period ** 2).rolling(bollinger_period - 1).sum().shift(1)

            window_sum = df[group_col].map(closed_sum) + df["Close"]
            window_sum_squared = df[group_col].map(closed_sum_squared) + df["Close"] ** 2

            basis = window_sum / bollinger_period
            variance = (window_sum_squared / bollinger_period - basis ** 2).clip(lower=0)
            std = variance ** 0.5

            out[f"bb_base_{horizon}"] = basis
            out[f"bb_upper_{horizon}"] = basis + num_std_deviations * std
            out[f"bb_lower_{horizon}"] = basis - num_std_deviations * std

        return out

    def get_rsi_features(self, daily_data) -> pd.DataFrame:
        wilder_smoothing_alpha = 1 / 14
        rsi_ma_length = 14

        df = self._add_time_group_columns(daily_data)

        out = pd.DataFrame(index=df.index)

        daily_change = df["Close"].diff()
        daily_avg_gain = daily_change.clip(lower=0).ewm(alpha=wilder_smoothing_alpha, adjust=False).mean()
        daily_avg_loss = (-daily_change).clip(lower=0).ewm(alpha=wilder_smoothing_alpha, adjust=False).mean()
        out["rsi_daily"] = 100 - 100 / (1 + daily_avg_gain / daily_avg_loss)
        out["rsi_ma_daily"] = out["rsi_daily"].rolling(rsi_ma_length).mean()
        out["rsi_gap_daily"] = out["rsi_daily"] - out["rsi_ma_daily"]

        for horizon, group_col in [("weekly", "week_id"), ("monthly", "month_id")]:
            close_by_period = df.groupby(group_col, sort=True)["Close"].last()

            period_change = close_by_period.diff()
            closed_avg_gain = period_change.clip(lower=0).ewm(alpha=wilder_smoothing_alpha, adjust=False).mean()
            closed_avg_loss = (-period_change).clip(lower=0).ewm(alpha=wilder_smoothing_alpha, adjust=False).mean()

            change_from_last_closed_period = df["Close"] - df[group_col].map(close_by_period.shift(1))

            current_avg_gain = wilder_smoothing_alpha * change_from_last_closed_period.clip(lower=0) + (1 - wilder_smoothing_alpha) * df[group_col].map(closed_avg_gain.shift(1))
            current_avg_loss = wilder_smoothing_alpha * (-change_from_last_closed_period).clip(lower=0) + (1 - wilder_smoothing_alpha) * df[group_col].map(closed_avg_loss.shift(1))

            current_rsi = 100 - 100 / (1 + current_avg_gain / current_avg_loss)
            closed_rsi = 100 - 100 / (1 + closed_avg_gain / closed_avg_loss)
            closed_rsi_sum = closed_rsi.rolling(rsi_ma_length - 1).sum().shift(1)

            out[f"rsi_{horizon}"] = current_rsi
            out[f"rsi_ma_{horizon}"] = (df[group_col].map(closed_rsi_sum) + current_rsi) / rsi_ma_length
            out[f"rsi_gap_{horizon}"] = current_rsi - out[f"rsi_ma_{horizon}"]

        return out

    def get_vix_features(self, daily_data, vix_daily=None) -> pd.DataFrame:
        df = self._add_time_group_columns(daily_data)

        df["vix_close"] = vix_daily["Close"].reindex(df.index, method="ffill")

        out = pd.DataFrame(index=df.index)

        out["vix_daily_last"] = df["vix_close"].shift(1)

        vix_close_by_week = df.groupby("week_id", sort=True)["vix_close"].last()
        vix_close_by_month = df.groupby("month_id", sort=True)["vix_close"].last()
        out["vix_weekly_last"] = df["week_id"].map(vix_close_by_week.shift(1))
        out["vix_monthly_last"] = df["month_id"].map(vix_close_by_month.shift(1))

        return out
    
    def trim_to_start_date(self, features_df, start_date=None) -> pd.DataFrame:
        if start_date is None:
            start_date = "2000-01-01"
        cutoff = str(start_date)[:10]
        return features_df[features_df.index > cutoff]
    