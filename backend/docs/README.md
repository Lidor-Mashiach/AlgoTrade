# Backend

> Data acquisition → feature engineering → sync → SQLite storage.
> Entry point: `main.py`.

---

## Contents

1. [Responsibilities](#responsibilities)
2. [Folder structure](#folder-structure)
3. [Data flow](#data-flow)
4. [Smart sync logic](#smart-sync-logic)
5. [Feature engineering](#feature-engineering)
6. [Storage](#storage)
7. [Configuration](#configuration)

---

## Responsibilities

- Fetch EOD OHLCV data for all configured tickers via **yfinance**.
- Compute the full feature table (see [FEATURES.md](FEATURES.md)) per ticker across daily, weekly, and monthly horizons.
- **Smart sync**: compare yfinance's latest available date against the DB's latest stored date per ticker — only fetch and recompute what is actually stale.
- Persist features to **SQLite**, split by horizon into three tables per ticker.

---

## Folder structure

```
backend/
├── config.json                   ← tickers, MA/BB periods, db filename
├── main.py                       ← entry point: load config → sync check → fetch → save
├── database.db                   ← SQLite database (git-ignored)
├── docs/
│   ├── README.md                 ← this file
│   └── FEATURES.md               ← authoritative feature catalog
├── eod_data/
│   ├── Ticker_EOD.py             ← data class wrapping one ticker/date snapshot
│   ├── Ticker_EOD_Extractor.py   ← computes all features from raw OHLCV
│   └── Ticker_EOD_Manager.py     ← fetches via yfinance, orchestrates extraction
├── storage/
│   ├── TickerDB.py               ← per-ticker SQLite access (daily/weekly/monthly tables)
│   └── TickersDBManager.py       ← multi-ticker wrapper over TickerDB
├── sync/
│   └── SyncManager.py            ← compares yfinance latest date vs DB latest date
└── utils/
    ├── ConsoleLogger.py          ← colored timestamped terminal logger
    └── Banner.py                 ← ASCII startup banner
```

---

## Data flow

```
config.json
    │
    ▼
main.py
    ├── TickersDBManager  ──────────────────────── SQLite (database.db)
    ├── SyncManager
    │       └── yf.Ticker.history()  ← latest date check per ticker
    │
    └── [unsynced tickers only]
            │
            ▼
        Tickers_EOD_Manager
            ├── yf.download()  ← bulk OHLCV fetch (daily, from 2000-01-01)
            └── Ticker_EOD_Extractor (per ticker)
                    └── computes all feature blocks
                            │
                            ▼
                    TickerDB.add_dataframe()  ──► SQLite
```

---

## Smart sync logic

`SyncManager.get_sync_status()` compares two dates for each ticker:

- **`yf_latest`** — most recent date available on yfinance (fetched via `1m` intraday history).
- **`db_latest`** — `MAX(date)` in the ticker's `_daily` table.

A ticker is considered **synced** when both dates match (string prefix comparison on `YYYY-MM-DD`).

`main.py` then:
1. Skips synced tickers entirely.
2. For unsynced tickers, fetches full OHLCV history from yfinance (since 2000-01-01) and trims to only the rows newer than `db_latest` before saving.

---

## Feature engineering

All feature computation lives in `Ticker_EOD_Extractor`. It takes:
- **`ticker_daily_data`** — raw OHLCV DataFrame for the ticker (daily, from yfinance).
- **`vix_daily_data`** — raw OHLCV DataFrame for `^VIX` (fetched alongside all tickers).
- **`periods`** — list of MA/BB periods (from config, default `[10, 50, 100, 150, 200]`).

Weekly and monthly aggregations are derived from the daily data using ISO week IDs (`YYYY-WW`) and month IDs (`YYYY-MM`), so no separate weekly/monthly downloads are needed.

The resulting DataFrame is split into three by column name pattern:

| Horizon | Column pattern |
|---------|----------------|
| Daily | contains `daily` or `prev_day` |
| Weekly | contains `weekly` or `week` |
| Monthly | contains `monthly` or `month` |

Full feature list: [FEATURES.md](FEATURES.md).

---

## Storage

SQLite via `TickerDB`. Each ticker gets **three tables**:

| Table | Columns |
|-------|---------|
| `{ticker}_daily` | `date` (PK) + all daily features |
| `{ticker}_weekly` | `date` (PK) + all weekly features |
| `{ticker}_monthly` | `date` (PK) + all monthly features |

Ticker names are sanitized for SQL: `.` → `_`, leading `^` removed (e.g. `^GDAXI` → `GDAXI`).

Writes use `INSERT OR REPLACE` (upsert), so re-running is safe.

`TickersDBManager` is a thin multi-ticker wrapper — it holds one `TickerDB` instance per ticker and delegates all reads/writes to it.

---

## Configuration

`config.json` (at `backend/config.json`):

```json
{
  "tickers":  ["SPY", "QQQ", "TA35.TA", "^TA125.TA", "^GDAXI", "^DJI"],
  "periods":  [10, 50, 100, 150, 200],
  "db_name":  "backend\\database.db"
}
```

| Key | Purpose |
|-----|---------|
| `tickers` | Tickers to fetch and store. `^VIX` is always fetched internally for VIX features but is not listed here. |
| `periods` | Window sizes used for SMA, EMA, and Bollinger Band calculations. |
| `db_name` | Path to the SQLite file (relative to project root). |
