# 📊 Feature Catalog

> **Single source of truth** for every feature the model consumes.
> This file is referenced by both the **Backend** (which *produces* these features)
> and the **AI** module (which *consumes* them).
> If a feature is added/removed, update it **here first**, then in the code.

All features are computed from **end-of-day (EOD) data only** — the system is *not* real-time.
"Current week / current month" means the still-open candle, measured up to the last closed daily candle.

---

## 1. Price & Returns

| # | Feature key | Description | Horizon | Unit |
|---|-------------|-------------|---------|------|
| 1 | `close_daily_last` | Close price of the last closed **daily** candle | Daily | price |
| 2 | `close_weekly_last` | Close price of the last closed **weekly** candle | Weekly | price |
| 3 | `close_monthly_last` | Close price of the last closed **monthly** candle | Monthly | price |
| 4 | `pct_change_daily_last` | % change of the last closed daily candle | Daily | % |
| 5 | `pct_change_week_current` | % change of the **open** (unfinished) weekly candle so far | Weekly | % |
| 6 | `pct_change_week_prev` | % change of the **last closed** weekly candle | Weekly | % |
| 7 | `pct_change_month_current` | % change of the **open** (unfinished) monthly candle so far | Monthly | % |
| 8 | `pct_change_month_prev` | % change of the **last closed** monthly candle | Monthly | % |

## 2. Moving Averages — Simple (SMA)

| # | Feature key | Description | Periods | Unit |
|---|-------------|-------------|---------|------|
| 9  | `sma_daily_{p}`   | Daily SMA | 50, 100, 150, 200 | price |
| 10 | `sma_weekly_{p}`  | Weekly SMA | 50, 100, 150, 200 | price |
| 11 | `sma_monthly_{p}` | Monthly SMA | 50, 100, 150, 200 | price |

## 3. Moving Averages — Exponential (EMA)

| # | Feature key | Description | Periods | Unit |
|---|-------------|-------------|---------|------|
| 12 | `ema_daily_{p}`   | Daily EMA | 50, 100, 150, 200 | price |
| 13 | `ema_weekly_{p}`  | Weekly EMA | 50, 100, 150, 200 | price |
| 14 | `ema_monthly_{p}` | Monthly EMA | 50, 100, 150, 200 | price |

> `{p}` expands to one column per period, e.g. `sma_daily_50`, `sma_daily_100`, ...

## 4. Volume

| # | Feature key | Description | Horizon | Unit |
|---|-------------|-------------|---------|------|
| 15 | `volume_prev_day`      | Volume of the previous daily candle | Daily | shares |
| 16 | `volume_avg_daily_90`  | Average daily volume over the last ~90 trading days | Daily | shares |
| 17 | `volume_week_current`  | Volume accumulated in the open weekly candle | Weekly | shares |
| 18 | `volume_week_prev`     | Volume of the last closed weekly candle | Weekly | shares |
| 19 | `volume_month_current` | Volume accumulated in the open monthly candle | Monthly | shares |
| 20 | `volume_month_prev`    | Volume of the last closed monthly candle | Monthly | shares |

## 5. Range (Low / High)

| # | Feature key | Description | Horizon | Unit |
|---|-------------|-------------|---------|------|
| 21 | `low_prev_day`, `high_prev_day`         | Low/High of previous daily candle | Daily | price |
| 22 | `low_week_current`, `high_week_current` | Low/High of the open weekly candle | Weekly | price |
| 23 | `low_week_prev`, `high_week_prev`       | Low/High of the last closed weekly candle | Weekly | price |
| 24 | `low_month_current`, `high_month_current` | Low/High of the open monthly candle | Monthly | price |
| 25 | `low_month_prev`, `high_month_prev`     | Low/High of the last closed monthly candle | Monthly | price |

## 6. Bollinger Bands

| # | Feature key | Description | Horizon | Unit |
|---|-------------|-------------|---------|------|
| 26 | `bb_upper_daily`, `bb_lower_daily`     | Bollinger upper/lower band (20, 2σ) | Daily | price |
| 27 | `bb_upper_weekly`, `bb_lower_weekly`   | Bollinger upper/lower band | Weekly | price |
| 28 | `bb_upper_monthly`, `bb_lower_monthly` | Bollinger upper/lower band | Monthly | price |

## 7. RSI

| # | Feature key | Description | Horizon | Unit |
|---|-------------|-------------|---------|------|
| 29 | `rsi_daily`   | RSI (14) on daily candles | Daily | 0–100 |
| 30 | `rsi_weekly`  | RSI (14) on weekly candles | Weekly | 0–100 |
| 31 | `rsi_monthly` | RSI (14) on monthly candles | Monthly | 0–100 |

## 8. VIX (market-wide fear gauge — **feature, not a prediction target**)

| # | Feature key | Description | Horizon | Unit |
|---|-------------|-------------|---------|------|
| 32 | `vix_daily_last`   | VIX close of last daily candle | Daily | index |
| 33 | `vix_weekly_last`  | VIX close of last weekly candle | Weekly | index |
| 34 | `vix_monthly_last` | VIX close of last monthly candle | Monthly | index |

---

## 🎯 Prediction Targets (labels)

For each `(index, horizon)` the model predicts the **% move of the next candle's close**
relative to the last closed candle, expressed as a **range with confidence**:

| Output | Description |
|--------|-------------|
| `pred_low`  | Lower bound of the expected close % move |
| `pred_high` | Upper bound of the expected close % move |
| `confidence` | Model confidence in the range (e.g. 0–1) |

> The range can be derived from a predicted mean ± k·σ, or from quantile regression.
> See `ai/README.md` for the modeling discussion.

---

## 🌐 Tracked Indices

| Display name | yfinance ticker | Notes |
|--------------|-----------------|-------|
| S&P 500 ETF | `SPY` | |
| Nasdaq 100 ETF | `QQQ` | |
| TA-35 | `TA35.TA` | **TA-25 → TA-35** (TA-25 was renamed/expanded to TA-35 in 2017; treat as one series) |
| TA-125 | `TA125.TA` | |
| DAX | `^GDAXI` | |
| Dow Jones | `^DJI` | |
| VIX | `^VIX` | **Feature only**, not a target |

> Ticker symbols are configurable in `config/settings.yaml`. Verify each symbol against the
> chosen data source before first run.
