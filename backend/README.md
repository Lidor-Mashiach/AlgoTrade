# 🔧 Backend (Logic Layer)

> Everything "behind the scenes": **data acquisition → feature engineering → smart sync →
> storage/auth → public API**. The CLI never touches data sources or the DB directly — it
> only talks to `backend/api.py`.
>
> 👤 **Owner:** Eran

---

## 🧭 Contents

1. [Responsibilities](#-responsibilities)
2. [Folder structure](#-folder-structure)
3. [Data sources](#-data-sources)
4. [Feature requirements](#-feature-requirements-full-table)
5. [Smart sync logic](#-smart-sync-logic)
6. [Storage & auth](#-storage--auth)
7. [Public API (logic ↔ CLI bridge)](#-public-api-logic--cli-bridge)
8. [Offline behavior](#-offline-behavior)

---

## 📋 Responsibilities

- 📥 **Acquire** EOD data for all tracked indices (yfinance **or** scraping — Eran's call).
- 🧱 **Build** the full feature table (see below) per `(index, horizon)`.
- 🔄 **Sync smartly**: pull/compute only what is stale; skip work if already up to date.
- 🗄️ **Persist** candles, features, and users (SQLite). Passwords stored **hashed only**.
- 🔌 **Expose** a clean Python API to the CLI (`market_snapshot`, `predict`, `register`, `login`, …).

---

## 📂 Folder structure

```
backend/
├── README.md
├── FEATURES.md            ← 📊 the feature catalog (shared with AI)
├── api.py                 ← public surface used by the CLI
├── data_sources/
│   ├── base.py            ← abstract DataSource interface
│   ├── yfinance_source.py ← default implementation (stub)
│   └── scraper_source.py  ← alternative implementation (stub)
├── features/
│   ├── indicators.py      ← SMA/EMA/RSI/Bollinger/VIX helpers (stubs)
│   └── feature_builder.py ← assembles the full feature vector
├── sync/
│   └── sync_manager.py    ← "how many candles did I miss" logic
└── storage/
    ├── db.py              ← SQLite schema & access
    └── auth.py            ← register/login, password hashing
```

---

## 🌐 Data sources

A `DataSource` is an **interface** (`data_sources/base.py`) so we can swap
**yfinance** ↔ **scraping** without touching the rest of the code.

| Method | Returns |
|--------|---------|
| `get_candles(ticker, interval, start, end)` | OHLCV DataFrame |
| `get_last_close(ticker, interval)` | last closed candle |
| `is_available()` | connectivity check (for offline handling) |

Default impl: `YFinanceSource`. Verify each ticker symbol (see `FEATURES.md`) before first run.

---

## 📊 Feature requirements (full table)

The complete, authoritative list of every feature the model receives lives in
**[`FEATURES.md`](FEATURES.md)** — price/returns, SMA, EMA, volume, range, Bollinger, RSI, VIX,
plus the prediction targets and the tracked-index ticker map.

> ✅ The **AI** module references the exact same file, so producer and consumer never drift.

A condensed view:

| Group | Features | Horizons |
|-------|----------|----------|
| Price & returns | close, % change (current & previous candle) | D / W / M |
| Moving averages | SMA & EMA × {50,100,150,200} | D / W / M |
| Volume | prev, 90-day avg, current & previous candle | D / W / M |
| Range | Low / High (current & previous candle) | D / W / M |
| Bollinger Bands | upper / lower | D / W / M |
| RSI | RSI(14) | D / W / M |
| VIX | last close (feature only) | D / W / M |

---

## 🔄 Smart sync logic

The system is **not real-time**. On launch it must:

1. Read `last_sync_at` from the DB.
2. Compute **how many daily / weekly / monthly candles closed** since then
   (using a trading calendar, after the ~01:00 Israel-time cutoff so the close is final).
3. Pull **only the missing candles**, recompute affected features, and update `last_sync_at`.
4. If everything is already current → **skip straight to inference**, no wasted calls.

```
last_sync = 5 trading days ago
            → fetch 5 new daily candles
            → maybe 1 new weekly candle closed → update
            → no new monthly candle → skip
```

> The same "missed N periods" number is handed to the AI module so it can decide whether an
> **incremental update** is needed (see `ai/README.md`).

---

## 🗄️ Storage & auth

- **SQLite** file under `data/` (git-ignored).
- Tables (suggested): `users`, `candles`, `features`, `meta` (holds `last_sync_at`).
- 🔐 **Passwords:** stored **hashed** (bcrypt + per-user salt). Login = hash the typed password
  and compare to the stored hash. **Decryption is forbidden** — there is nothing to decrypt.

---

## 🔌 Public API (logic ↔ CLI bridge)

`api.py` is the **only** module the CLI imports. Suggested surface:

| Function | Purpose |
|----------|---------|
| `market_snapshot()` | indices + last-close direction/%, FX rates (for guest screen) |
| `sync_if_needed()` | run smart sync; returns what was updated |
| `predict(index, horizon, amount=None, currency=None)` | forecast range, confidence, recommendation, optional profit range |
| `get_series(index, horizon)` | price series up to last close (for charts) |
| `register(first, last, email, password)` / `login(email, password)` | auth |
| `update_profile(...)` | settings screen |

---

## 🌐 Offline behavior

Any data pull is wrapped so that **loss of connectivity never crashes the app**:
catch the network error → return a typed result the CLI renders as a friendly
*"Internet connection required for this action"* popup, while cached data stays usable.
