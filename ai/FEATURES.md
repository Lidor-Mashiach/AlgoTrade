# 🧬 Feature catalog (AI model facing)

This document lists the features the models actually consume, after feature engineering.
It complements the raw data catalog owned by the backend. The raw catalog describes what
the data layer produces. This catalog describes what enters the boosters.

Everything here is produced inside `PreTraining/Feature-Eng/build_features.py` and stored
per horizon in the intermediate data store. The exact indicator conventions live in the
main `README.md`.

---

## 🧭 Conventions

- **One label, three quantiles.** Each horizon has a single real label. The Q10, Q50, and
  Q90 boosters all train on the same features and the same label. Only the pinball alpha
  differs between them.
- **Anchor close.** The running daily close at each row's date is the universal anchor. It
  is the denominator of the label and the reference close in every relative feature, which
  keeps the engineering consistent with the intra-candle convention. The anchor is a helper
  column and is never fed to the model.
- **Scale.** Every percentage feature and the label are expressed in percentage points, for
  example a value of 1.5 means a move of one and a half percent.
- **No scaling.** LightGBM is scale invariant, so there is no z-score and no normalization.
  Raw numeric columns enter as they are.
- **Ticker is a feature.** The index identity enters as a native categorical feature, which
  lets one pooled model still specialize per index.
- **Missing values.** LightGBM handles missing values natively. Warm-up rows created by the
  long moving averages are dropped during feature engineering.

---

## 🎯 Label

| Horizon | Label column | Definition |
| --- | --- | --- |
| daily | `target_daily` | Percent move from the current daily close to the next day's close |
| weekly | `target_weekly` | Percent move from the row's anchor to the in-progress week's closing value |
| monthly | `target_monthly` | Percent move from the row's anchor to the in-progress month's closing value |

The label is the only place that looks forward. No feature uses any future information. Rows
whose candle has not closed yet are dropped, because their label is not realized.

---

## 📅 Daily features

**Engineered**

| Feature | Built from | Meaning |
| --- | --- | --- |
| `dist_sma_daily_{20,50,100,150,200}` | anchor close and `sma_daily_{p}` | Percent distance of the close above or below each simple moving average |
| `dist_ema_daily_{20,50,100,150,200}` | anchor close and `ema_daily_{p}` | Percent distance of the close from each exponential moving average |
| `bb_pctb_daily` | anchor close and the daily Bollinger bands | Position of the close inside the band, zero at the lower band and one at the upper band |
| `bb_width_daily` | the daily Bollinger bands | Band width over its base, a volatility proxy |
| `rel_vol_daily` | `volume_prev_day` and `volume_avg_daily_90` | Recent volume relative to its ninety-day average |
| `range_pct_daily` | `high_prev_day`, `low_prev_day`, anchor close | Previous day's high to low range as a percent of the close |
| `realized_vol_daily` | `pct_change_daily_last` | Rolling standard deviation of daily returns |
| `dow_sin`, `dow_cos` | the date | Cyclical encoding of the day of week |
| `month_sin`, `month_cos` | the date | Cyclical encoding of the month of year |

**Passthrough (raw, entered unchanged)**

| Feature | Meaning |
| --- | --- |
| `pct_change_daily_last` | Percent move of the last completed daily candle |
| `rsi_daily` | Relative strength index |
| `rsi_ma_daily` | Moving average of the relative strength index |
| `rsi_gap_daily` | Gap between the relative strength index and its moving average |
| `vix_daily_last` | Volatility index level |
| `ticker` | Index identity, a categorical feature |

---

## 🗓️ Weekly features

**Engineered**

| Feature | Built from | Meaning |
| --- | --- | --- |
| `dist_sma_weekly_{20,50,100,150,200}` | anchor close and `sma_weekly_{p}` | Percent distance of the running close from each weekly simple moving average |
| `dist_ema_weekly_{20,50,100,150,200}` | anchor close and `ema_weekly_{p}` | Percent distance from each weekly exponential moving average |
| `bb_pctb_weekly` | anchor close and the weekly Bollinger bands | Position of the close inside the weekly band |
| `bb_width_weekly` | the weekly Bollinger bands | Weekly band width over its base |
| `rel_vol_week_current` | `volume_week_current` and `volume_week_prev` | This week's volume relative to last week's |
| `range_pct_week_prev` | `high_week_prev`, `low_week_prev`, anchor close | Previous week's range as a percent of the close |
| `realized_vol_weekly` | `pct_change_week_prev` | Rolling standard deviation of weekly returns |
| `days_to_close_weekly` | the date | Trading days left until the week closes, as a fraction |
| `month_sin`, `month_cos` | the date | Cyclical encoding of the month of year |

**Passthrough (raw, entered unchanged)**

| Feature | Meaning |
| --- | --- |
| `pct_change_week_current` | Percent move of the week so far |
| `pct_change_week_prev` | Percent move of the last completed week |
| `rsi_weekly` | Weekly relative strength index |
| `rsi_ma_weekly` | Moving average of the weekly relative strength index |
| `rsi_gap_weekly` | Gap between the weekly relative strength index and its moving average |
| `vix_weekly_last` | Volatility index level on the weekly view |
| `ticker` | Index identity, a categorical feature |

---

## 📆 Monthly features

**Engineered**

| Feature | Built from | Meaning |
| --- | --- | --- |
| `dist_sma_monthly_{20,50,100,150,200}` | anchor close and `sma_monthly_{p}` | Percent distance of the running close from each monthly simple moving average |
| `dist_ema_monthly_{20,50,100,150,200}` | anchor close and `ema_monthly_{p}` | Percent distance from each monthly exponential moving average |
| `bb_pctb_monthly` | anchor close and the monthly Bollinger bands | Position of the close inside the monthly band |
| `bb_width_monthly` | the monthly Bollinger bands | Monthly band width over its base |
| `rel_vol_month_current` | `volume_month_current` and `volume_month_prev` | This month's volume relative to last month's |
| `range_pct_month_prev` | `high_month_prev`, `low_month_prev`, anchor close | Previous month's range as a percent of the close |
| `realized_vol_monthly` | `pct_change_month_prev` | Rolling standard deviation of monthly returns |
| `days_to_close_monthly` | the date | Trading days left until the month closes, as a fraction |
| `month_sin`, `month_cos` | the date | Cyclical encoding of the month of year |

**Passthrough (raw, entered unchanged)**

| Feature | Meaning |
| --- | --- |
| `pct_change_month_current` | Percent move of the month so far |
| `pct_change_month_prev` | Percent move of the last completed month |
| `rsi_monthly` | Monthly relative strength index |
| `rsi_ma_monthly` | Moving average of the monthly relative strength index |
| `rsi_gap_monthly` | Gap between the monthly relative strength index and its moving average |
| `vix_monthly_last` | Volatility index level on the monthly view |
| `ticker` | Index identity, a categorical feature |

---

## 🚫 Columns the model never sees

These are present in the raw tables but are dropped before training. Raw price levels are
non-stationary, so the model uses relative features built from them instead.

- **Raw price levels.** `close_{daily,weekly,monthly}_last`, every `sma_*` and `ema_*`, the
  Bollinger base, upper, and lower bands, and the raw high, low, and volume columns.
- **Helpers.** The anchor close and the candle period identifier, used only to build the
  label and the group-aware split.

---

## 🗒️ Notes

- Features are only created when their raw inputs are present. On partial data, a feature
  with a missing input is skipped and reported, so the pipeline still runs end to end.
- `days_to_close` uses a business-day approximation that ignores market holidays until a
  real trading calendar is wired into the data layer.
