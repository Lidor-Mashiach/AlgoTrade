# 📈 Algo-Trade — Index Candle Forecasting & Recommendation System

> A local, **non-real-time** algorithmic-trading *advisory* system built for the
> "Algo-Trade" course. It learns historical patterns from major indices and forecasts
> the expected **% move of the next candle's close** (daily / weekly / monthly),
> as a **range** `[low, high]` with a **confidence** score — then turns that into a
> Long / Short / Stay-out recommendation.

---

## 🧭 Table of Contents

1. [What it does](#-what-it-does)
2. [Core idea](#-core-idea)
3. [Architecture at a glance](#-architecture-at-a-glance)
4. [Project layout](#-project-layout)
5. [The three pillars](#-the-three-pillars)
6. [Data flow](#-data-flow)
7. [Responsibilities](#-responsibilities)
8. [Getting started](#-getting-started)
9. [Design decisions & open questions](#-design-decisions--open-questions)
10. [Disclaimer](#-disclaimer)

---

## 🎯 What it does

- Tracks major indices: **SPY, QQQ, TA-35, TA-125, DAX, Dow Jones** (+ **VIX** as a feature).
- For each index and each **horizon** (📅 daily / 📆 weekly / 🗓️ monthly) it forecasts the
  next candle's close as a **range with confidence**, relative to the last closed candle.
- The closer we are to the candle's close, the **more information** and **less time-to-change**
  → confidence is expected to rise and the range to tighten.
- Wraps the forecast in a friendly UI: market overview, login, prediction screen, and a
  position-sizing helper ("if I invest X, what's my expected profit range?").

> ⚠️ It does **not** trade live. It is a recommendation/learning tool.

---

## 💡 Core idea

| Concept | Choice |
|---------|--------|
| **Latency model** | Batch / EOD. Data is pulled once after market close (~01:00 Israel time). |
| **Prediction unit** | Range `[low%, high%]` + `confidence`, not a single point. |
| **Why a range** | Markets are noisy; a band (e.g. mean ± k·σ or quantiles) is honest and actionable. |
| **Recommendation rule** | range fully positive → **Long**, fully negative → **Short**, straddles 0 → **Stay out**. |
| **Smart sync** | On launch the system detects how many days/weeks/months it missed and updates *only* what's needed — no wasteful re-pulls or full re-training. |

---

## 🏗️ Architecture at a glance

```
                 ┌──────────────────────────────────────────────┐
                 │                    CLI (UI)                    │
                 │  guest home · auth · user home · prediction ·  │
                 │            settings · charts                   │
                 └───────────────┬────────────────────────────────┘
                                 │  request (index, horizon, …)
                                 ▼
                 ┌──────────────────────────────────────────────┐
                 │                  BACKEND (logic)               │
                 │  data sources · feature builder · sync mgr ·   │
                 │            storage/auth · public API           │
                 └───────────────┬────────────────────────────────┘
                                 │  feature vector
                                 ▼
                 ┌──────────────────────────────────────────────┐
                 │                      AI                        │
                 │  datasets · models (per index × horizon?) ·    │
                 │   training · incremental update · inference    │
                 └────────────────────────────────────────────────┘
```

---

## 📂 Project layout

```
algo-trade/
├── README.md                ← you are here (high-level)
├── bootstrap.py             ← one-time: pull history + train all models
├── requirements.txt
├── .gitignore
├── config/
│   └── settings.example.yaml
├── data/                    ← cached candles + SQLite DB (git-ignored)
├── backend/                 ← 🔧 data, features, sync, storage, API   → backend/README.md
├── ai/                      ← 🧠 datasets, models, training, inference → ai/README.md
└── cli/                     ← 🖥️ presentation layer (screens & charts) → cli/README.md
```

---

## 🏛️ The three pillars

### 🔧 `backend/` — "behind the scenes"
Pulls EOD data (yfinance **or** scraping — *Eran decides*), builds the full
[feature table](backend/FEATURES.md), runs the **smart sync** that figures out what's stale,
manages the **SQLite** database and **hashed** user auth, and exposes a clean API to the CLI.
👉 Deep dive: [`backend/README.md`](backend/README.md)

### 🧠 `ai/` — the brain
Owns datasets (train/val/test), the model(s), training and **incremental update**
(so we don't retrain from scratch on every new candle), and inference that returns
`(low, high, confidence)`.
👉 Deep dive: [`ai/README.md`](ai/README.md)

### 🖥️ `cli/` — the face
Everything the user sees from launch onward: guest market overview, login/register,
personalized home, the prediction screen (index × horizon picker, profit estimator,
interactive zoomable charts), and settings.
👉 Deep dive: [`cli/README.md`](cli/README.md)

---

## 🔄 Data flow

1. **Launch** → CLI calls `backend.api.market_snapshot()` for the guest overview.
2. **Sync** → backend asks: *"how many candles did I miss since last run?"* and pulls only those.
3. **Predict** → user picks `(index, horizon)`; CLI → `backend.api.predict(...)` → AI inference.
4. **Render** → CLI shows the range, confidence, Long/Short/Stay-out, and the chart with the
   forecast band highlighted to the right of the last candle.

---

## 👥 Responsibilities

| Pillar | Owner | Scope |
|--------|-------|-------|
| 🔧 Backend / data | **Eran** | data acquisition, features, sync, storage, API |
| 🧠 AI | **You (me)** | datasets, models, training, incremental update, inference |
| 🖥️ CLI | *(shared / TBD)* | UI, screens, charts, auth flow |

---

## 🚀 Getting started

There are **three phases**: one-time **setup**, a one-time **bootstrap** (history + first training),
and the **routine run** you do every session. The smart sync makes the routine run cheap.

### 1️⃣ Setup (once)

```bash
python -m venv .venv
source .venv/bin/activate                              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config/settings.example.yaml config/settings.yaml   # then edit (tickers, history depth, paths)
```

### 2️⃣ Bootstrap — *first time only* (and after a long gap)

This is the heavy step: it pulls the historical candles and trains every model.
Run it **once** before the first launch.

```bash
python bootstrap.py            # 1) pull history  2) build features  3) train all (index × horizon)
```

> ⏳ This can take a while (downloads + training). Subsequent launches do **not** repeat it —
> they only catch up on the few candles that closed since last time.

### 3️⃣ Routine run — *every session* (this is "going live")

```bash
streamlit run cli/app.py       # default UI (see cli/README.md)
```

On launch the app **automatically**:

| Step | What happens |
|------|--------------|
| 🔄 **Smart sync** | `api.sync_if_needed()` checks how many daily/weekly/monthly candles closed since `last_sync_at` and pulls **only** those (nothing if already current). |
| 🧠 **Incremental update** | if candles were missed, the AI does a `partial_fit` on them — **no full retrain**. |
| 🖥️ **Serve** | the UI opens on the guest market-overview screen, ready to predict. |

```
launch ─▶ sync_if_needed() ─▶ missed? ──no──▶ serve UI
                                  │
                                 yes ─▶ pull missing candles ─▶ partial_fit ─▶ serve UI
```

### 🔁 The lifecycle in one picture

```
[setup once]  ──▶  [bootstrap once]  ──▶  [routine run] ⟲ (sync → update → serve, every session)
```

> 🌐 **No internet?** Data pulls fail gracefully with a clear message
> ("Internet connection required for this action") — the app never crashes; cached data stays usable.
>
> ⏰ **EOD timing:** run after the `eod_cutoff_israel` time in `config/settings.yaml` (~01:00),
> so the candles you pull are the *final* closes.

---

## 🧩 Design decisions & open questions

| Topic | Current default | Status |
|-------|-----------------|--------|
| UI framework | Streamlit + Plotly (web, hover, zoom, fullscreen) | 🔓 open — you called it "CLI"; a true terminal can't do hover/zoom |
| Data source | yfinance | 🔓 open — Eran: API vs scraping |
| One model vs many | per `(index × horizon)` | 🔓 open — discussed in `ai/README.md` |
| Incremental training | `partial_fit` / warm-start, keep a rolling window | 🔓 open — discussed in `ai/README.md` |
| History depth | TBD | 🔓 open — to decide before training |
| DB | SQLite | ✅ chosen (local, simple) |
| Password storage | hashed (bcrypt), **never** reversible | ✅ chosen |

---

## ⚠️ Disclaimer

This is an academic project. It is **not** financial advice and does **not** execute trades.
Forecasts are statistical estimates and can be wrong, especially around unexpected events.
