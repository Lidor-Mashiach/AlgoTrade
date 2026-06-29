"""
Stage 5 - Train/test split.

Splits each horizon's engineered table into train and test sets with three guarantees:
  - the split is at the candle (group) level first, so the intra-candle rows of one
    candle never straddle train and test (the window follows the split, not the reverse)
  - the test set is held out per ticker and time-ordered, so every index is represented
    in proportion and the test period is the most recent (no look-ahead)
  - a group_id column is kept in both parts so GroupKFold during training can keep whole
    candles inside a single fold

Output is one train file and one test file per horizon in the intermediate data store.
A short size summary is written to results/.
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

import numpy as np
import pandas as pd

import config
from utils import io_store, plotting

# ----------------------------------------------------------------------------------
# GLOBAL PARAMETERS
# ----------------------------------------------------------------------------------
HORIZONS = config.HORIZONS
TEST_SIZE = config.TEST_SIZE
GROUP_COLUMN = "group_id"


def candle_group(df: pd.DataFrame, horizon: str) -> pd.Series:
    """
    Candle identifier per row. For daily, each row is its own candle. For weekly and
    monthly, all intra-candle rows of the same ticker and period share one id, so the
    whole candle moves to the same side of the split.
    """
    date = pd.to_datetime(df["Date"], errors="coerce")
    if horizon == "weekly":
        iso = date.dt.isocalendar()
        period = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    elif horizon == "monthly":
        period = date.dt.year * 100 + date.dt.month
    else:
        period = pd.Series(np.arange(len(df)), index=df.index)
    return df["ticker"].astype(str) + "_" + period.astype(str)


def split_one(df: pd.DataFrame, horizon: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (train_df, test_df) for one horizon using a per-ticker, time-ordered holdout."""
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df[GROUP_COLUMN] = candle_group(df, horizon)

    test_groups: list[str] = []
    for ticker, block in df.groupby("ticker"):
        # Order this ticker's candles in time, hold out the most recent fraction.
        ordered = (
            block[[GROUP_COLUMN, "Date"]]
            .groupby(GROUP_COLUMN)["Date"].min()
            .sort_values()
        )
        n_test = max(1, int(round(len(ordered) * TEST_SIZE)))
        test_groups.extend(ordered.index[-n_test:].tolist())

    test_mask = df[GROUP_COLUMN].isin(set(test_groups))
    train_df = df[~test_mask].reset_index(drop=True)
    test_df = df[test_mask].reset_index(drop=True)
    return train_df, test_df


def run() -> None:
    """Split every horizon and persist the train and test parts."""
    out_dir = plotting.prepare_results_dir("tables", "split")
    summary_rows = []

    for horizon in HORIZONS:
        df = io_store.read_features(horizon)
        train_df, test_df = split_one(df, horizon)

        io_store.write_split(train_df, horizon, "train")
        io_store.write_split(test_df, horizon, "test")

        total = len(train_df) + len(test_df)
        test_pct = round(100.0 * len(test_df) / total, 2) if total else 0.0
        summary_rows.append({
            "horizon": horizon,
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "test_pct": test_pct,
            "train_groups": train_df[GROUP_COLUMN].nunique(),
            "test_groups": test_df[GROUP_COLUMN].nunique(),
        })
        print(f"[split] {horizon}: train={len(train_df)} test={len(test_df)} "
              f"({test_pct}% test)")

    pd.DataFrame(summary_rows).to_csv(out_dir / "split_summary.csv", index=False)
    print("[split] done")


if __name__ == "__main__":
    run()
