# 🧠 AI Module

> The single source of truth for the **AI side** of Algo-Trade — folder layout, model
> architecture, the exact features each horizon model consumes, required transformations, the
> inference contract, and the development pipeline.
> Owner: **Lidor**. Backend and CLI are owned by the other developers (see root `README.md`).

This document assumes the **raw feature catalog** in [`../backend/FEATURES.md`](../backend/FEATURES.md).
Here we decide what the **model** actually eats — which raw columns enter as they are, which are
turned into new features, and which features still need to be added.

---

## 🧭 Contents

1. [Folder structure](#-folder-structure)
2. [Model architecture](#-model-architecture)
3. [Why LightGBM](#-why-lightgbm)
4. [Why three quantiles (Q10 / Q50 / Q90)](#-why-three-quantiles-q10--q50--q90)
5. [History depth per horizon](#-history-depth-per-horizon)
6. [Ticker pooling, imbalance, and why not single stocks](#-ticker-pooling-imbalance-and-why-not-single-stocks)
7. [Handling small data](#-handling-small-data)
8. [Prediction targets](#-prediction-targets)
9. [Backend storage and how the AI separates features](#-backend-storage-and-how-the-ai-separates-features)
10. [Feature tables (per horizon)](#-feature-tables)
11. [Features that must still be added](#-features-that-must-still-be-added)
12. [Indicator parameters and conventions](#-indicator-parameters-and-conventions)
13. [Inference contract](#-inference-contract)
14. [Retraining logic](#-retraining-logic)
15. [Development pipeline](#-development-pipeline)

---

## 📂 Folder structure

```
ai/
├── README.md                          ← you are here (the authoritative AI spec)
├── FEATURES.md                        ← model-facing feature catalog (engineered + passthrough)
├── config.py                          ← global constants, paths, and model path helpers
├── run_pipeline.py                    ← top-level runner: stage 1 → 2 → 3
│
├── utils/                             ← shared helpers (no stage number, used everywhere)
│   ├── gpu.py                         ← LightGBM device resolution with CPU fallback
│   ├── plotting.py                    ← non-interactive figures and results-folder handling
│   ├── io_store.py                    ← intermediate data store between stages
│   ├── runner.py                      ← step runner behind every folder runner
│   └── modeling.py                    ← shared model code and hyperparameters (stages 2 and 3)
│
├── 1_PreTraining/
│   ├── README.md
│   ├── run_pretraining.py             ← runner: extract → check missing → features → EDA → split
│   ├── Data-Extraction/
│   │   └── extract_dataset.py         ← pool per-ticker tables, split by suffix into 3 horizons
│   └── Feature-Eng/
│       ├── check_missing.py           ← missing-value report and basic cleaning
│       ├── build_features.py          ← relative features and the label, drop raw price columns
│       ├── run_eda.py                 ← correlation heatmap and non-linear association
│       └── split_dataset.py           ← group-aware, per-ticker proportional train/test split
│
├── 2_Train/
│   ├── README.md
│   ├── run_train.py                   ← runner: train all horizons, then evaluate on test
│   ├── train_core.py                  ← stage-2 engine (GroupKFold, learning curves, dev models)
│   ├── train_daily.py                 ← thin per-horizon wrappers
│   ├── train_weekly.py
│   ├── train_monthly.py
│   ├── test_core.py                   ← shared evaluation engine (metrics and figures)
│   ├── test_daily.py
│   ├── test_weekly.py
│   └── test_monthly.py
│
├── 3_Production-FinalTraining/
│   ├── README.md
│   ├── run_final_training.py          ← runner: build production models, then smoke test
│   ├── build_final_models.py          ← refit on all data, save the 9 production boosters
│   ├── predictor.py                   ← returns {low, mid, high, confidence}
│   └── verify_inference.py            ← loads the models and runs a dummy prediction
│
├── Evaluation/                        ← library, called from stage 2 (no stage number)
│   ├── README.md                      ← what each metric means, why it was chosen, the advantage here
│   └── metrics.py                     ← coverage, band width, pinball, confusion matrix, and more
│
├── Inference_models/                  ← the 9 production boosters that ship, per horizon (tracked)
│   ├── daily/      (q10.txt · q50.txt · q90.txt · metadata.json)
│   ├── weekly/     (q10.txt · q50.txt · q90.txt · metadata.json)
│   └── monthly/    (q10.txt · q50.txt · q90.txt · metadata.json)
│
├── dev_models/                        ← stage-2 development boosters, diagnostic only (git-ignored)
├── data_store/                        ← intermediate data that flows between stages (git-ignored)
└── results/                           ← latest run only, non-interactive
    ├── plots/                         ← figures (EDA, learning curves, interval, confusion)
    ├── reports/                       ← readable markdown summaries
    ├── metrics/                       ← metric values as JSON, pinball per quantile
    └── tables/                        ← CSV tables (correlations, association, feature lists)
```

> Note vs. the early scaffold. There is **no** incremental or warm-start training file — we
> settled on **full retrain only** (see the Retraining logic section). Boosters are keyed by
> `(horizon, quantile)`, not `(index, horizon)`, because the ticker is a **feature**, not a
> separate model. Each pipeline folder is driven by its own runner with a commentable `STEPS`
> list, and `run_pipeline.py` chains the three folder runners end to end.

---

## 🏗️ Model architecture

| Layer | Count | Detail |
|-------|-------|--------|
| **Logical models** | **3** | one per horizon — `daily`, `weekly`, `monthly` |
| **Boosters (artifacts)** | **9** | 3 horizons × 3 quantiles (Q10, Q50, Q90) |
| **Datasets** | **3** | one per horizon, each **pooled** across all tickers |

The 3 quantile boosters inside one horizon **share the same dataset** — same `X`, same `y`. They
differ only in the loss they minimize (see the quantile section). The model type is **LightGBM**
with quantile regression.

```
dataset_daily   ──▶ booster_daily_q10 · booster_daily_q50 · booster_daily_q90
dataset_weekly  ──▶ booster_weekly_q10 · booster_weekly_q50 · booster_weekly_q90
dataset_monthly ──▶ booster_monthly_q10 · booster_monthly_q50 · booster_monthly_q90
```

---

## 🌲 Why LightGBM

- **Tabular data with engineered features means gradient-boosted trees beat deep learning** at
  this data scale. This is a well-established result. Neural nets need far more data and shine on
  raw signals, not hand-built indicators like ours.
- **A few thousand rows per ticker** means a neural net would overfit, while a regularized tree
  ensemble will not.
- **Built-in quantile regression** gives the prediction range directly, with no extra machinery.
- **Native categorical features** let `ticker` enter cleanly, with no one-hot blow-up.
- **Fast full retrain** (seconds to minutes) fits our retrain-when-a-new-candle-closes logic.
- **LightGBM over XGBoost** because it is lighter and faster with native categoricals. The
  difference is small, and XGBoost is a valid drop-in.

Deep learning stays a later experiment only if gradient boosting underperforms. Note that the
intra-candle sampling we use (see Handling small data) does **not** justify deep learning — those
extra rows are highly correlated, not independent information.

---

## 🎯 Why three quantiles (Q10 / Q50 / Q90)

A normal regression model predicts **one number** — the average expected outcome. It cannot
express a range. To get a range we ask the model three different questions.

| Booster | Question it answers | Role |
|---------|--------------------|------|
| **Q10** | the value only 10% of outcomes fall below | lower bound of the range |
| **Q50** | the median outcome | the central, most-accurate forecast |
| **Q90** | the value 90% of outcomes fall below | upper bound of the range |

So the band **[Q10, Q90]** is an **80% interval** — historically, about 80% of closes landed
inside it. The coverage level (80 to 85%) is a **global variable**, not user-selectable.

### The key idea — the label does NOT carry the quantile

This is the part that feels paradoxical, so read it slowly. The label is **a single real value** —
the actual percent move that happened. It is **not** "the Q10 value" or "the Q90 value". There is
one label per row, shared by all three boosters of that horizon (see How the label column is
built). So the question is real — how do three models with the **same rows, the same label, and the
same hyperparameters** end up predicting three **different** numbers?

The answer is the **loss function**, and nothing else. A model learns by minimizing its loss. If
you change *how the loss counts an error*, you change *where the model settles*, even though the
data never changed.

### The asymmetric loss (pinball / quantile loss)

Normal regression uses a **symmetric** loss — predicting 2 too high is just as bad as 2 too low,
so the model settles on the **average**. Quantile regression uses a **lopsided** loss controlled by
one number, the target quantile (call it `q`, where Q10 means q = 0.1, Q90 means q = 0.9).

```
error = actual − predicted

loss =        q   * error      when error >= 0   (we predicted too LOW)
loss =   (q − 1)  * error      when error <  0   (we predicted too HIGH)
```

Plug in the numbers:

- **Q90** (q = 0.9). Predicting too low costs `0.9 * error`. Predicting too high costs `0.1 * error`.
  Being too low hurts **9 times more**, so to minimize total loss the model deliberately aims
  **high** — it settles at the line only about 10% of real outcomes exceed. That line *is* the 90th
  percentile.
- **Q10** (q = 0.1). The mirror image — being too high hurts 9 times more, so the model aims low and
  settles at the 10th percentile.
- **Q50** (q = 0.5). Both sides cost the same. The model settles in the middle — the median.

That single number `q` is the **only** thing that differs between the three boosters. Same data,
same label, same tree depth and learning rate. In LightGBM it is literally:

```python
LGBMRegressor(objective="quantile", alpha=0.10, **shared_params)  # Q10
LGBMRegressor(objective="quantile", alpha=0.50, **shared_params)  # Q50
LGBMRegressor(objective="quantile", alpha=0.90, **shared_params)  # Q90
```

**Intuition.** Imagine estimating your commute, with a penalty for guessing wrong. If arriving
**late** (you guessed too short) is punished 9 times harder than arriving early, you will quote a
**conservative, high** number — say 45 minutes even when the average is 30 — because lateness is
expensive. That conservative-high estimate is exactly Q90. Equal penalties would give you the
median. Same trip, same history, different penalty, different answer.

### Why we predict a band instead of chasing perfection

Markets contain real randomness. A model that claims a single perfect number is **overfitting**,
not accuracy, and overconfidence is the **most dangerous** thing when money is involved. The
**Q50 is where we chase accuracy**. The Q10 and Q90 band is an honest measure of what we do
**not** know. The band can be **asymmetric** (for example minus 4% to plus 2%), which matches
reality, because market drops are sharper than rises. A symmetric mean plus or minus 2 sigma
would miss this.

### No separate fine-tuning between the three

The three boosters of one horizon **share the same hyperparameters** (tree depth, leaves,
learning rate). Only the penalty ratio changes. So hyperparameter tuning happens **once per
horizon**, three times total, not nine. Different **horizons** do get separate tuning, because
monthly needs heavier regularization (see Handling small data).

---

## 📅 History depth per horizon

The three models are independent, so each may use a different look-back window.

| Horizon | History | Reason |
|---------|---------|--------|
| `daily` | from about 2010 | plenty of rows already, and older daily data is noisier and structurally different |
| `weekly` | from about 2010 | same as daily |
| `monthly` | **as deep as possible, toward 1993** | monthly has very few rows, so deep history is the **only** way to let the model see crash events (2000 dot-com, 2008) needed to learn the lower tail (Q10). Monthly candles are slow and stable, so old data hurts less. |

US indices reach back further (SPY 1993, DJI much earlier). Israeli indices are younger, which
feeds directly into the imbalance handling below.

---

## ⚖️ Ticker pooling, imbalance, and why not single stocks

**Why pool all indices into one dataset per horizon.** Pooling does **not** mean every ticker
gets the same prediction. At inference you feed the **specific** ticker's features (its RSI, its
volatility, its `ticker` id) and get a specific output. Pooling means the model learns **one
function** from state to forecast, trained on examples from all indices, because the rule
"high RSI plus low volatility leads to expected move X" is roughly universal across indices. The
payoff is **data volume** — monthly jumps from about 180 rows per ticker to about 1,080 pooled.

**Imbalance (tickers with different history lengths).** If SPY contributes 380 monthly rows and
TA-125 only about 180, the model leans toward SPY. This is **not** class imbalance, because the
label is continuous. It is over-representation of one ticker. The fix is **sample weighting per
ticker** (up-weight rows from under-represented tickers), **not** oversampling. The `ticker`
feature lets the model still specialize where a ticker genuinely differs.

**Why NOT add single stocks (AAPL, GOOG) or meme stocks (GME).** Pooling works only because
indices are **homogeneous** — each is an average of hundreds of companies, so their dynamics are
smooth and comparable. A single stock is driven by company-specific noise (earnings, CEO, one
product). A pump-and-dump like GME is driven by manipulation and sentiment, where our indicators
(RSI, MA, Bollinger) are meaningless. Mixing them in would **poison the pool**. Indices in,
single names out.

---

## 📉 Handling small data

Three combined defenses.

1. **Pooling** (above) multiplies rows by the number of tickers.
2. **Intra-candle sampling** (weekly and monthly only). Instead of one row per week, emit one row
   per trading day inside the week, each with the features available **at that moment** and the
   **same** final target. Weekly goes from about 780 to about 3,780 samples. These rows are
   correlated, so the train/test split must be **group-based** (all rows of one candle on the
   same side) to avoid leakage. This also requires the `time_to_close` feature (see the next
   section).
3. **Heavy regularization for monthly** — shallow trees, high minimum samples per leaf, low
   learning rate. Monthly will be the least confident model, and that is acceptable. A wide band
   honestly signals low confidence.

---

## 🎯 Prediction targets

Each model predicts the **percent move of the next or current candle's close** vs. the last known
daily close. We predict **percent change**, never raw price, because price is not stationary while
percent is, and percent is comparable across tickers.

| Target | Definition |
|--------|------------|
| `target_daily` | (close_next_day / close_today) − 1 |
| `target_weekly` | (close_at_week_end / last_daily_close) − 1 |
| `target_monthly` | (close_at_month_end / last_daily_close) − 1 |

### How the label column is built

The label is **not** in the raw data. The AI pipeline creates it by **looking forward** and
attaching each row's future outcome to the row, using a backward shift of the next candle's close.

- **One label per horizon, not per quantile.** The three boosters (Q10, Q50, Q90) of a horizon all
  train on the **same** `y` — the actual percent move that happened. They differ only in the loss,
  not in the label. So there are exactly **three** label columns total (`target_daily`,
  `target_weekly`, `target_monthly`).
- **The label is a single real value, not a quantile.** It does not represent Q10, Q50, or Q90 — it
  is just what happened. The three quantiles are produced entirely by the asymmetric loss at
  training time (see The key idea and The asymmetric loss under Why three quantiles). The same label
  feeds all three, and the loss is what splits them apart.
- ⚠️ **Looking forward is allowed for the label only.** It must **never** touch the features (`X`).
  Any feature that peeks at future data is **leakage**, and the model will look perfect in training
  and fail in reality. The extractor already guards this with `shift(1)` and `prev` columns. Keep
  that discipline when building the label.

---

## 🗄️ Backend storage and how the AI separates features

### How the backend stores it — one database per ticker

The data layer keeps **one database (or table) per ticker** — `SPY`, `QQQ`, `TA35`, and so on —
each holding only that ticker's **raw** rows. It does **not** split storage by horizon. Every row
is one trading day and is **wide**: it carries the daily, weekly, and monthly raw columns together,
exactly as the extractor produced them. The only addition needed for pooling is a `ticker` column
(or it is implied by which database the row came from).

So responsibility splits cleanly:

- **Backend** — raw data, one database per ticker, wide rows, no horizon split.
- **AI (my side)** — at the data-extraction stage, read those per-ticker tables, stack them into
  one pooled table (adding `ticker`), then separate features by horizon and build the labels.

### How the AI separates features per horizon — by name suffix

The wide row is not "daily" or "weekly". The AI module selects columns **by their name suffix**,
using the per-horizon tables in this document as the authoritative list:

- **daily dataset** — columns ending in or containing `_daily` or `_prev_day`, plus the shared columns.
- **weekly dataset** — columns containing `_week` or `_weekly`, plus the shared columns.
- **monthly dataset** — columns containing `_month` or `_monthly`, plus the shared columns.

No column name collides across horizons (every name carries its own horizon token), so the split is
unambiguous — there is no risk of a weekly column being mistaken for a daily one.

**Shared columns** added to all three datasets: `ticker` and `Date`. The cyclical date features
`month_sin` and `month_cos` are also shared, **but note they are not raw** — the AI must **create**
them from `Date` during feature engineering, the same as `realized_vol` and `days_to_close`.

**VIX is not shared** — each horizon has its own (`vix_daily_last`, `vix_weekly_last`,
`vix_monthly_last`), so each goes only to its matching dataset.

---

## 📊 Feature tables

**How to read the columns.**

- **Meaning** — what the feature represents.
- **Transformation** — how the value is produced or rescaled before training. LightGBM is
  scale-invariant (a split depends on the order of values, not their magnitude), so raw numeric
  columns need **no rescaling** and enter as they are. The real work is turning raw prices into
  relative quantities and adding the missing features.
- **Feature engineering?** —
  - **no** means a **raw** column that already exists in the extractor output and in
    `../backend/FEATURES.md`. It either enters the model as it is, or it is raw material that the
    model does not use directly.
  - **yes** means a **new** column created inside the AI pipeline by feature engineering. This
    covers both brand-new features (such as realized volatility) and rescaled or transformed
    versions of a raw column. The source raw column or columns are listed.
- **Into model?** — whether this column is fed to the model. Raw price columns are **no**, because
  they exist only to engineer a relative feature from them.
- 🆕 marks a feature **not produced by the current extractor** that must still be added (see the
  Features that must still be added section).

Period set `{p}` is `{20, 50, 100, 150, 200}`, so each `{p}` row expands to 5 columns.

### 📅 Daily model

| Feature | Meaning | Transformation | Feature engineering? | Into model? |
|---------|---------|----------------|----------------------|-------------|
| `ticker` 🆕 | which index this row belongs to | native categorical | no (raw, must be added to extraction) | ✅ |
| `close_daily_last` | last daily close (price) | none (raw anchor) | no | ❌ |
| `pct_change_daily_last` | percent move of last daily candle | as is | no | ✅ |
| `sma_daily_{p}` | daily simple moving averages (price) | none | no | ❌ |
| `ema_daily_{p}` | daily exponential moving averages (price) | none | no | ❌ |
| `dist_sma_daily_{p}` | percent distance of price from each daily SMA | ratio (close − sma) / sma | yes ← `close_daily_last`, `sma_daily_{p}` | ✅ |
| `dist_ema_daily_{p}` | percent distance of price from each daily EMA | ratio (close − ema) / ema | yes ← `close_daily_last`, `ema_daily_{p}` | ✅ |
| `bb_base_daily`, `bb_upper_daily`, `bb_lower_daily` | daily Bollinger lines (price) | none | no | ❌ |
| `bb_pctb_daily` | where price sits inside the daily band, 0 lower to 1 upper | (close − lower) / (upper − lower) | yes ← `close`, `bb_upper_daily`, `bb_lower_daily` | ✅ |
| `bb_width_daily` | daily band width, a volatility proxy | (upper − lower) / base | yes ← daily Bollinger lines | ✅ |
| `rsi_daily` | daily momentum, 0 to 100 | as is | no | ✅ |
| `rsi_ma_daily` | smoothed daily RSI | as is | no | ✅ |
| `rsi_gap_daily` | RSI minus its MA, momentum acceleration | as is (already a difference) | no (already in extractor) | ✅ |
| `volume_prev_day`, `volume_avg_daily_90` | raw daily volumes | none | no | ❌ |
| `rel_vol_daily` | yesterday's volume vs its 90-day average | ratio (volume / avg) | yes ← `volume_prev_day`, `volume_avg_daily_90` | ✅ |
| `low_prev_day`, `high_prev_day` | yesterday's low and high (price) | none | no | ❌ |
| `range_pct_daily` | yesterday's high-low range as percent of close | (high − low) / close | yes ← `high_prev_day`, `low_prev_day`, `close` | ✅ |
| `vix_daily_last` | global risk sentiment, implied vol of S&P | as is | no | ✅ |
| `realized_vol_daily` 🆕 | the index's own recent volatility (local) | rolling std of returns | yes ← `pct_change_daily_last` | ✅ |
| `dow_sin`, `dow_cos` 🆕 | day of week, cyclically encoded | sin and cos of 2π·dow/5 | yes ← `Date` | ✅ |
| `month_sin`, `month_cos` 🆕 | month-of-year seasonality | sin and cos of 2π·month/12 | yes ← `Date` | ✅ |

Daily has **no** `time_to_close`. It always forecasts a full next-day candle (the system runs
after market close).

### 📆 Weekly model

| Feature | Meaning | Transformation | Feature engineering? | Into model? |
|---------|---------|----------------|----------------------|-------------|
| `ticker` 🆕 | which index this row belongs to | native categorical | no (raw, must be added to extraction) | ✅ |
| `close_weekly_last` | last closed weekly close (price) | none (raw anchor) | no | ❌ |
| `pct_change_week_current` | percent move of the open week so far | as is | no | ✅ |
| `pct_change_week_prev` | percent move of the last closed week | as is | no | ✅ |
| `sma_weekly_{p}`, `ema_weekly_{p}` | weekly moving averages (price) | none | no | ❌ |
| `dist_sma_weekly_{p}` | percent distance of price from each weekly SMA | ratio (close − sma) / sma | yes ← `close_weekly_last`, `sma_weekly_{p}` | ✅ |
| `dist_ema_weekly_{p}` | percent distance of price from each weekly EMA | ratio (close − ema) / ema | yes ← `close_weekly_last`, `ema_weekly_{p}` | ✅ |
| `bb_base_weekly`, `bb_upper_weekly`, `bb_lower_weekly` | weekly Bollinger lines (price) | none | no | ❌ |
| `bb_pctb_weekly` | price position inside the weekly band | (close − lower) / (upper − lower) | yes ← `close`, weekly Bollinger lines | ✅ |
| `bb_width_weekly` | weekly band width | (upper − lower) / base | yes ← weekly Bollinger lines | ✅ |
| `rsi_weekly` | weekly momentum, 0 to 100 | as is | no | ✅ |
| `rsi_ma_weekly` | smoothed weekly RSI | as is | no | ✅ |
| `rsi_gap_weekly` | weekly RSI minus its MA | as is (already a difference) | no (already in extractor) | ✅ |
| `volume_week_current`, `volume_week_prev` | raw weekly volumes | none | no | ❌ |
| `rel_vol_week_current` | current-week volume vs previous week | ratio (current / prev) | yes ← `volume_week_current`, `volume_week_prev` | ✅ |
| `low_week_current`, `high_week_current`, `low_week_prev`, `high_week_prev` | weekly low and high (price) | none | no | ❌ |
| `range_pct_week_prev` | last week's high-low range as percent | (high − low) / close | yes ← `high_week_prev`, `low_week_prev`, `close` | ✅ |
| `vix_weekly_last` | global risk sentiment, weekly | as is | no | ✅ |
| `realized_vol_weekly` 🆕 | the index's own weekly realized volatility | rolling std of weekly returns | yes ← weekly returns | ✅ |
| `days_to_close_weekly` 🆕 | trading days left until the week closes, drives confidence | count or fraction of 5 | yes ← `Date` plus calendar | ✅ |
| `month_sin`, `month_cos` 🆕 | month-of-year seasonality | sin and cos of 2π·month/12 | yes ← `Date` | ✅ |

### 🗓️ Monthly model

| Feature | Meaning | Transformation | Feature engineering? | Into model? |
|---------|---------|----------------|----------------------|-------------|
| `ticker` 🆕 | which index this row belongs to | native categorical | no (raw, must be added to extraction) | ✅ |
| `close_monthly_last` | last closed monthly close (price) | none (raw anchor) | no | ❌ |
| `pct_change_month_current` | percent move of the open month so far | as is | no | ✅ |
| `pct_change_month_prev` | percent move of the last closed month | as is | no | ✅ |
| `sma_monthly_{p}`, `ema_monthly_{p}` | monthly moving averages (price) | none | no | ❌ |
| `dist_sma_monthly_{p}` | percent distance of price from each monthly SMA | ratio (close − sma) / sma | yes ← `close_monthly_last`, `sma_monthly_{p}` | ✅ |
| `dist_ema_monthly_{p}` | percent distance of price from each monthly EMA | ratio (close − ema) / ema | yes ← `close_monthly_last`, `ema_monthly_{p}` | ✅ |
| `bb_base_monthly`, `bb_upper_monthly`, `bb_lower_monthly` | monthly Bollinger lines (price) | none | no | ❌ |
| `bb_pctb_monthly` | price position inside the monthly band | (close − lower) / (upper − lower) | yes ← `close`, monthly Bollinger lines | ✅ |
| `bb_width_monthly` | monthly band width | (upper − lower) / base | yes ← monthly Bollinger lines | ✅ |
| `rsi_monthly` | monthly momentum, 0 to 100 | as is | no | ✅ |
| `rsi_ma_monthly` | smoothed monthly RSI | as is | no | ✅ |
| `rsi_gap_monthly` | monthly RSI minus its MA | as is (already a difference) | no (already in extractor) | ✅ |
| `volume_month_current`, `volume_month_prev` | raw monthly volumes | none | no | ❌ |
| `rel_vol_month_current` | current-month volume vs previous month | ratio (current / prev) | yes ← `volume_month_current`, `volume_month_prev` | ✅ |
| `low_month_current`, `high_month_current`, `low_month_prev`, `high_month_prev` | monthly low and high (price) | none | no | ❌ |
| `range_pct_month_prev` | last month's high-low range as percent | (high − low) / close | yes ← `high_month_prev`, `low_month_prev`, `close` | ✅ |
| `vix_monthly_last` | global risk sentiment, monthly | as is | no | ✅ |
| `realized_vol_monthly` 🆕 | the index's own monthly realized volatility | rolling std of monthly returns | yes ← monthly returns | ✅ |
| `days_to_close_monthly` 🆕 | trading days left until the month closes, drives confidence | count or fraction of about 21 | yes ← `Date` plus calendar | ✅ |
| `month_sin`, `month_cos` 🆕 | month-of-year seasonality | sin and cos of 2π·month/12 | yes ← `Date` | ✅ |

---

## 🆕 Features that must still be added

These are **not** produced by the current extractor. Some can be engineered from existing raw
columns with no new data pull. Others need the data layer to supply more.

| Feature | How to obtain | Needs the data layer? |
|---------|---------------|------------------------|
| `ticker` | the extractor must include a ticker column when pooling multiple indices | yes, add the column |
| `realized_vol_{daily,weekly,monthly}` | rolling std of the existing `pct_change_*` returns | no, engineer in AI |
| `days_to_close_{weekly,monthly}` | from `Date` plus a trading calendar | no, engineer in AI (needs a calendar) |
| `dow_sin`, `dow_cos`, `month_sin`, `month_cos` | cyclical encoding of `Date` | no, engineer in AI |
| all `dist_*`, `bb_pctb_*`, `bb_width_*`, `rel_vol_*`, `range_pct_*` | engineered from existing raw price and volume columns | no, engineer in AI |

**Action item for the data layer.** The only thing the data layer must change is **adding a
`ticker` column** so pooled rows are distinguishable. Everything else is engineered inside the AI
pipeline.

---

## ⚙️ Indicator parameters and conventions

Confirmed against the extractor source. Useful when engineering features so you match the raw
computation exactly.

- **MA periods** — 20, 50, 100, 150, 200, for both SMA and EMA.
- **Bollinger** — period 20, k of 2 sigma, population std (ddof of 0). `bb_base` is the 20-period
  SMA.
- **RSI** — Wilder's RSI, length 14. `rsi_ma` is the simple 14-period MA of the RSI. `rsi_gap` is
  RSI minus `rsi_ma`.
- **Volume average** — `volume_avg_daily_90` is the rolling 90-day mean.
- **Returns scale** — every `pct_change_*` is in **percentage points** (already times 100). Do
  **not** multiply again when engineering `realized_vol`.
- **VIX lag** — `vix_daily_last` is the **previous** day's VIX (D minus 1). Weekly and monthly use
  the last closed week or month. VIX is forward-filled onto each index's own trading calendar,
  which handles US vs. TA vs. DAX holiday gaps with no leakage.
- **Intra-candle convention** — weekly and monthly SMA, EMA, Bollinger, and RSI **fold in the
  current running candle's close**, so the current value moves within the candle. This is
  intentional and aligns with the intra-candle sampling design. A row dated mid-week already
  reflects the week so far, so the engineered `dist_*` and `bb_pctb_*` measure distance from an
  average that includes today, by design.

---

## 🔌 Inference contract

The single entry point the backend calls. Keep this signature stable.

```python
# 3_Production-FinalTraining/predictor.py
def predict(ticker: str, horizon: str, features: dict) -> dict:
    """
    Returns:
        {"low": float, "high": float, "confidence": float}
        # low  = Q10  (lower bound, percent move)
        # high = Q90  (upper bound, percent move)
        # mid  = Q50  (median, optional but useful)
        # confidence is derived from band width (Q90 minus Q10).
        #            A tighter band means higher confidence.
    """
```

**Recommendation mapping** (done in backend or CLI, not here). A band that is fully positive maps
to **Long**, fully negative maps to **Short**, and a band that straddles zero maps to **Stay out**.

---

## 🔁 Retraining logic

- **Always** pull data up to today (dynamic) and recompute fresh features, because inference needs
  the latest values regardless of training.
- **Full retrain** from the start date. **Never** gradient-boosting continued-training, because it
  just stacks more trees and degrades quality.
- A flag **`last_trained_through`** (per horizon) records the **last candle the model was trained
  on**. Retrain only if `last_trained_through` is earlier than the latest closed candle. Same day
  or market closed means no new candle, so skip training and go straight to inference. This is
  candle-based, not clock-based, so it never retrains twice on the same candle.

---

## 🛠️ Development pipeline

Ordered stages, each a separate script driven by a main runner. Graphs are written to a
`results/` subfolder, and **only the latest run is kept**. Matplotlib must run **non-interactively**
(no blocking pop-up windows), using a non-GUI backend and saving to file.

| Stage | Name | Notes |
|-------|------|-------|
| 1 | **Data extraction** | read the per-ticker raw file (template path for now, no real file yet) |
| 2 | **Missing-value check** | inspect and handle NaNs (the warm-up rows of long moving averages are expected) |
| 3 | **Feature engineering** | build `dist_*`, `bb_pctb`, `bb_width`, `rel_vol`, `range_pct`, `realized_vol`, `time_to_close`, and cyclical date features, drop raw price columns |
| 4 | **EDA** | correlation heatmap (linear) plus non-linear association checks, then decide drops |
| 5 | **Split** | train, validation, test. Group-aware (no candle leakage) and time-ordered, with the train set representative of the test set |
| 6 | **Training** | per horizon, per quantile. Detect CUDA and use the GPU, otherwise the CPU |
| 7 | **Evaluation and tuning** | validate, tune hyperparameters (once per horizon), write a report |
| 8 | **Test run** | final unbiased evaluation on the held-out test set |
| 9 | **Save inference models** | persist the 9 boosters to `artifacts/` |

The order of stages 3 and 4 is flexible. A light EDA before feature engineering is fine to spot
raw issues, with the heavier EDA after. The runner decides. This is a recommended default.
