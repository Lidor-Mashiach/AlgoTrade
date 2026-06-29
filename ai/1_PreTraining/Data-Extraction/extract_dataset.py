"""
Stage 1 - Data extraction.

Reads the raw, wide, per-ticker tables that the backend owns, pools them into one
table with a ticker column, and splits that wide table into three per-horizon raw
datasets by column-name suffix. The output is written to the intermediate data store
for the feature-engineering stage to pick up.

BOUNDARY: this file must not contain backend logic. The only backend touch point is
load_raw_ticker_table, which is a thin adapter. Wire it to the real backend data API
(or drop a template file per ticker) without moving backend responsibilities here.
"""

from __future__ import annotations

# --- make the ai/ root importable regardless of where this script is launched from ---
import sys
import pathlib

for _parent in pathlib.Path(__file__).resolve().parents:
    if (_parent / "config.py").exists() and (_parent / "utils").is_dir():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break

import pandas as pd

import config
from utils import io_store

# ----------------------------------------------------------------------------------
# GLOBAL PARAMETERS (file specific knobs on top, shared constants come from config)
# ----------------------------------------------------------------------------------
TICKERS = config.TICKERS
HORIZONS = config.HORIZONS
SHARED_COLUMNS = config.SHARED_COLUMNS

# How each horizon's columns are recognized inside the wide row. No column name
# collides across horizons, so suffix matching is unambiguous.
HORIZON_TOKENS = {
    "daily": ("_daily", "_prev_day"),
    "weekly": ("_week", "_weekly"),
    "monthly": ("_month", "_monthly"),
}

# Raw column that holds the current daily close. Copied into the universal anchor used
# by the label and the relative features. Adjust the name if the backend differs.
DAILY_CLOSE_COLUMN = "close_daily_last"


# ----------------------------------------------------------------------------------
# Backend boundary: data access adapter
# ----------------------------------------------------------------------------------
def load_raw_ticker_table(ticker: str) -> pd.DataFrame:
    """
    Return the backend's raw, wide table for one ticker.

    Expected schema (one row per trading day, wide):
        - 'Date'                          a parseable date
        - 'close_daily_last', 'sma_daily_20', ... the daily raw columns
        - 'pct_change_week_current', ...  the weekly raw columns
        - 'pct_change_month_current', ... the monthly raw columns
      See ../../FEATURES.md and the per-horizon tables in ../../README.md for the
      full catalog. Pooling does not require the backend to add anything except,
      ideally, a ticker column. This adapter adds ticker if it is missing.

    TODO (data layer): replace the template read below with a real backend call,
    for example a query against the per-ticker database. Keep this function thin.
    """
    template_path = config.TEMPLATE_DATA_DIR / f"{ticker}.parquet"
    if template_path.exists():
        df = pd.read_parquet(template_path)
        if "ticker" not in df.columns:
            df["ticker"] = ticker
        return df

    raise NotImplementedError(
        f"No data source wired for ticker '{ticker}'. "
        f"Either connect the backend data API inside load_raw_ticker_table, "
        f"or drop a template table at {template_path}. "
        f"The expected return is a wide per-ticker raw DataFrame as described in "
        f"FEATURES.md and README.md."
    )


# ----------------------------------------------------------------------------------
# Pooling and splitting
# ----------------------------------------------------------------------------------
def pool_tickers(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Stack the per-ticker tables into one pooled table. Each row keeps its ticker, which
    is what lets a single pooled model still specialize per index. This is also where
    the well-known extractor issue is neutralized: by stacking explicitly per ticker we
    never overwrite one ticker's rows with another's.
    """
    frames = []
    for ticker, df in tables.items():
        df = df.copy()
        df["ticker"] = ticker
        frames.append(df)
    pooled = pd.concat(frames, ignore_index=True)

    # Universal anchor close, used by the label and the relative features. Kept as a
    # helper column in every horizon dataset and dropped before the model sees it.
    if DAILY_CLOSE_COLUMN in pooled.columns:
        pooled[config.ANCHOR_CLOSE] = pooled[DAILY_CLOSE_COLUMN]
    else:
        print(f"[extract] WARNING: '{DAILY_CLOSE_COLUMN}' missing, "
              f"'{config.ANCHOR_CLOSE}' not set. Label building will be limited.")

    if "Date" in pooled.columns:
        pooled["Date"] = pd.to_datetime(pooled["Date"], errors="coerce")
        pooled = pooled.sort_values(["ticker", "Date"]).reset_index(drop=True)
    return pooled


def select_horizon_columns(pooled: pd.DataFrame, horizon: str) -> pd.DataFrame:
    """
    Build one horizon's raw dataset by selecting columns whose name carries that
    horizon's token, plus the shared columns. Shared columns are added explicitly so
    they are never duplicated by token matching.
    """
    tokens = HORIZON_TOKENS[horizon]
    shared_present = [c for c in SHARED_COLUMNS if c in pooled.columns]
    horizon_cols = [
        c for c in pooled.columns
        if c not in SHARED_COLUMNS and any(tok in c for tok in tokens)
    ]
    selected = shared_present + horizon_cols
    return pooled[selected].copy()


def run() -> None:
    """Pull every ticker, pool, split by horizon, and persist the raw datasets."""
    print(f"[extract] loading {len(TICKERS)} ticker tables")
    tables = {ticker: load_raw_ticker_table(ticker) for ticker in TICKERS}

    pooled = pool_tickers(tables)
    print(f"[extract] pooled table: {pooled.shape[0]} rows, {pooled.shape[1]} columns")

    for horizon in HORIZONS:
        horizon_df = select_horizon_columns(pooled, horizon)
        out = io_store.write_raw(horizon_df, horizon)
        print(f"[extract] {horizon}: {horizon_df.shape[1]} columns -> {out}")

    print("[extract] done")


if __name__ == "__main__":
    run()
