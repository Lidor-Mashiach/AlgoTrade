# Feature Catalog

> Single source of truth for every feature the model consumes.
> Referenced by both the **Backend** (which *produces* features) and the **AI** module (which *consumes* them).
> If a feature is added or removed, update this file first, then the code.

All features are computed from **end-of-day (EOD) data only** — the system is not real-time.
"Current week / current month" means the still-open candle, measured up to the last closed daily candle.

---

## 1. Price & Returns

| Feature key | Description | Horizon | Unit |
|-------------|-------------|---------|------|
| `close_daily_last` | Close price of the last closed daily candle | Daily | price |
| `pct_change_daily_last` | % change of the last closed daily candle | Daily | % |
| `close_weekly_last` | Close price of the last closed weekly candle | Weekly | price |
| `pct_change_week_current` | % change of the open (unfinished) weekly candle so far | Weekly | % |
| `pct_change_week_prev` | % change of the last closed weekly candle | Weekly | % |
| `close_monthly_last` | Close price of the last closed monthly candle | Monthly | price |
| `pct_change_month_current` | % change of the open (unfinished) monthly candle so far | Monthly | % |
| `pct_change_month_prev` | % change of the last closed monthly candle | Monthly | % |

## 2. Moving Averages — Simple (SMA)

Computed for periods: **10, 50, 100, 150, 200** → keys expand to e.g. `sma_daily_10`, `sma_daily_50`, ...

| Feature key | Description | Horizon | Unit |
|-------------|-------------|---------|------|
| `sma_daily_{p}` | Daily SMA over `p` candles | Daily | price |
| `sma_weekly_{p}` | Weekly SMA — last `p-1` closed weekly closes + current close | Weekly | price |
| `sma_monthly_{p}` | Monthly SMA — last `p-1` closed monthly closes + current close | Monthly | price |

## 3. Moving Averages — Exponential (EMA)

Computed for periods: **10, 50, 100, 150, 200** → keys expand to e.g. `ema_daily_10`, `ema_daily_50`, ...

| Feature key | Description | Horizon | Unit |
|-------------|-------------|---------|------|
| `ema_daily_{p}` | Daily EMA (span=`p`, `adjust=False`) | Daily | price |
| `ema_weekly_{p}` | EMA updated with today's close against last closed weekly EMA | Weekly | price |
| `ema_monthly_{p}` | EMA updated with today's close against last closed monthly EMA | Monthly | price |

> Smoothing factor: α = 2 / (p + 1)

## 4. Volume

| Feature key | Description | Horizon | Unit |
|-------------|-------------|---------|------|
| `volume_prev_day` | Volume of the previous daily candle | Daily | shares |
| `volume_avg_daily_90` | Rolling 90-day average daily volume | Daily | shares |
| `volume_week_current` | Cumulative volume in the open weekly candle | Weekly | shares |
| `volume_week_prev` | Total volume of the last closed weekly candle | Weekly | shares |
| `volume_month_current` | Cumulative volume in the open monthly candle | Monthly | shares |
| `volume_month_prev` | Total volume of the last closed monthly candle | Monthly | shares |

## 5. Range (Low / High)

| Feature key | Description | Horizon | Unit |
|-------------|-------------|---------|------|
| `low_prev_day` | Low of the previous daily candle | Daily | price |
| `high_prev_day` | High of the previous daily candle | Daily | price |
| `low_week_current` | Running low of the open weekly candle | Weekly | price |
| `high_week_current` | Running high of the open weekly candle | Weekly | price |
| `low_week_prev` | Low of the last closed weekly candle | Weekly | price |
| `high_week_prev` | High of the last closed weekly candle | Weekly | price |
| `low_month_current` | Running low of the open monthly candle | Monthly | price |
| `high_month_current` | Running high of the open monthly candle | Monthly | price |
| `low_month_prev` | Low of the last closed monthly candle | Monthly | price |
| `high_month_prev` | High of the last closed monthly candle | Monthly | price |

## 6. Bollinger Bands

Parameters: **period = 20, σ = 2**, population std (ddof=0).

| Feature key | Description | Horizon | Unit |
|-------------|-------------|---------|------|
| `bb_base_daily` | Middle band (20-period SMA) | Daily | price |
| `bb_upper_daily` | Upper band (base + 2σ) | Daily | price |
| `bb_lower_daily` | Lower band (base − 2σ) | Daily | price |
| `bb_base_weekly` | Middle band on weekly close series | Weekly | price |
| `bb_upper_weekly` | Upper band on weekly close series | Weekly | price |
| `bb_lower_weekly` | Lower band on weekly close series | Weekly | price |
| `bb_base_monthly` | Middle band on monthly close series | Monthly | price |
| `bb_upper_monthly` | Upper band on monthly close series | Monthly | price |
| `bb_lower_monthly` | Lower band on monthly close series | Monthly | price |

## 7. RSI

Parameters: **Wilder smoothing** (α = 1/14), RSI MA window = 14.

| Feature key | Description | Horizon | Unit |
|-------------|-------------|---------|------|
| `rsi_daily` | RSI computed on daily closes | Daily | 0–100 |
| `rsi_ma_daily` | 14-period rolling MA of `rsi_daily` | Daily | 0–100 |
| `rsi_gap_daily` | `rsi_daily` − `rsi_ma_daily` | Daily | points |
| `rsi_weekly` | RSI updated with current close vs last closed weekly close | Weekly | 0–100 |
| `rsi_ma_weekly` | 14-period rolling MA of `rsi_weekly` | Weekly | 0–100 |
| `rsi_gap_weekly` | `rsi_weekly` − `rsi_ma_weekly` | Weekly | points |
| `rsi_monthly` | RSI updated with current close vs last closed monthly close | Monthly | 0–100 |
| `rsi_ma_monthly` | 14-period rolling MA of `rsi_monthly` | Monthly | 0–100 |
| `rsi_gap_monthly` | `rsi_monthly` − `rsi_ma_monthly` | Monthly | points |

## 8. VIX (market-wide fear gauge — feature only, not a prediction target)

VIX data (`^VIX`) is fetched internally alongside all tickers and is not listed in `config.json`.

| Feature key | Description | Horizon | Unit |
|-------------|-------------|---------|------|
| `vix_daily_last` | VIX close of the previous daily candle | Daily | index |
| `vix_weekly_last` | VIX close of the last closed weekly candle | Weekly | index |
| `vix_monthly_last` | VIX close of the last closed monthly candle | Monthly | index |

---

## Prediction Targets (labels)

For each `(ticker, horizon)` the model predicts the **% move of the next candle's close**
relative to the last closed candle, expressed as a range with confidence:

| Output | Description |
|--------|-------------|
| `pred_low` | Lower bound of the expected close % move |
| `pred_high` | Upper bound of the expected close % move |
| `confidence` | Model confidence in the range (0–1) |

---

## Tracked Tickers

Configured in `config.json` under the `"tickers"` key.

| Display name | Ticker symbol | Notes |
|--------------|---------------|-------|
| S&P 500 ETF | `SPY` | |
| Nasdaq 100 ETF | `QQQ` | |
| TA-35 | `TA35.TA` | TA-25 was renamed/expanded to TA-35 in 2017; treated as one series |
| TA-125 | `^TA125.TA` | |
| DAX | `^GDAXI` | |
| Dow Jones | `^DJI` | |
| VIX | `^VIX` | Fetched internally for VIX features; not a prediction target |

## MA / BB Periods

Configured in `config.json` under the `"periods"` key.
Default: `[10, 50, 100, 150, 200]`
