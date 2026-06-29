"""
Stage 3 - Feature engineering.

Turns raw price and volume columns into the relative, stationary features the model
actually consumes, adds the features that the extractor does not produce (realized
volatility, days to close, cyclical date encodings), builds the forward-looking label,
and drops the raw price columns. Output is one engineered table per horizon, written
to the intermediate data store.

Conventions follow README.md and FEATURES.md exactly. The running daily close (the
universal anchor) is used as "close" in every relative feature, consistent with the
intra-candle convention. Looking forward is allowed for the label only and never
touches a feature.
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
from pandas.tseries.offsets import MonthEnd

import config
from utils import io_store, plotting

# ----------------------------------------------------------------------------------
# GLOBAL PARAMETERS
# ----------------------------------------------------------------------------------
HORIZONS = config.HORIZONS
MA_PERIODS = config.MA_PERIODS
ANCHOR = config.ANCHOR_CLOSE
REALIZED_VOL_WINDOW = config.REALIZED_VOL_WINDOW
TRADING_DAYS = config.TRADING_DAYS_PER_CANDLE

# Per-horizon column-name spec. Keeps the engineering generic while matching the exact
# raw names from FEATURES.md. 'passthrough' columns enter the model unchanged.
HORIZON_SPEC = {
    "daily": {
        "key": "daily",
        "rel_vol": {"out": "rel_vol_daily", "num": "volume_prev_day", "den": "volume_avg_daily_90"},
        "range": {"out": "range_pct_daily", "high": "high_prev_day", "low": "low_prev_day"},
        "rvol": {"out": "realized_vol_daily", "ret": "pct_change_daily_last"},
        "days_to_close": None,
        "cyclical": ["dow", "month"],
        "passthrough": ["pct_change_daily_last", "rsi_daily", "rsi_ma_daily",
                        "rsi_gap_daily", "vix_daily_last"],
    },
    "weekly": {
        "key": "weekly",
        "rel_vol": {"out": "rel_vol_week_current", "num": "volume_week_current", "den": "volume_week_prev"},
        "range": {"out": "range_pct_week_prev", "high": "high_week_prev", "low": "low_week_prev"},
        "rvol": {"out": "realized_vol_weekly", "ret": "pct_change_week_prev"},
        "days_to_close": "days_to_close_weekly",
        "cyclical": ["month"],
        "passthrough": ["pct_change_week_current", "pct_change_week_prev", "rsi_weekly",
                        "rsi_ma_weekly", "rsi_gap_weekly", "vix_weekly_last"],
    },
    "monthly": {
        "key": "monthly",
        "rel_vol": {"out": "rel_vol_month_current", "num": "volume_month_current", "den": "volume_month_prev"},
        "range": {"out": "range_pct_month_prev", "high": "high_month_prev", "low": "low_month_prev"},
        "rvol": {"out": "realized_vol_monthly", "ret": "pct_change_month_prev"},
        "days_to_close": "days_to_close_monthly",
        "cyclical": ["month"],
        "passthrough": ["pct_change_month_current", "pct_change_month_prev", "rsi_monthly",
                        "rsi_ma_monthly", "rsi_gap_monthly", "vix_monthly_last"],
    },
}


# ----------------------------------------------------------------------------------
# Small numeric helpers
# ----------------------------------------------------------------------------------
def safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    """Element-wise division that returns NaN where the denominator is zero or missing."""
    den = den.replace(0, np.nan)
    return num / den


def has(df: pd.DataFrame, *cols: str) -> bool:
    """True only if every named column exists. Used to skip features on partial data."""
    return all(c in df.columns for c in cols)


# ----------------------------------------------------------------------------------
# Feature builders (each appends columns and records the engineered feature names)
# ----------------------------------------------------------------------------------
def add_distance_features(df: pd.DataFrame, key: str, built: list[str]) -> None:
    """Percent distance of the running close from each SMA and EMA."""
    for p in MA_PERIODS:
        sma = f"sma_{key}_{p}"
        ema = f"ema_{key}_{p}"
        if has(df, ANCHOR, sma):
            name = f"dist_sma_{key}_{p}"
            df[name] = safe_div(df[ANCHOR] - df[sma], df[sma])
            built.append(name)
        if has(df, ANCHOR, ema):
            name = f"dist_ema_{key}_{p}"
            df[name] = safe_div(df[ANCHOR] - df[ema], df[ema])
            built.append(name)


def add_bollinger_features(df: pd.DataFrame, key: str, built: list[str]) -> None:
    """Position inside the band (percent b) and band width as a volatility proxy."""
    base, upper, lower = f"bb_base_{key}", f"bb_upper_{key}", f"bb_lower_{key}"
    if has(df, ANCHOR, upper, lower):
        name = f"bb_pctb_{key}"
        df[name] = safe_div(df[ANCHOR] - df[lower], df[upper] - df[lower])
        built.append(name)
    if has(df, base, upper, lower):
        name = f"bb_width_{key}"
        df[name] = safe_div(df[upper] - df[lower], df[base])
        built.append(name)


def add_relative_volume(df: pd.DataFrame, spec: dict, built: list[str]) -> None:
    """Recent volume relative to a baseline volume (a participation signal)."""
    rv = spec["rel_vol"]
    if has(df, rv["num"], rv["den"]):
        df[rv["out"]] = safe_div(df[rv["num"]], df[rv["den"]])
        built.append(rv["out"])


def add_range_pct(df: pd.DataFrame, spec: dict, built: list[str]) -> None:
    """High-low range expressed as a percent of the running close."""
    rg = spec["range"]
    if has(df, rg["high"], rg["low"], ANCHOR):
        df[rg["out"]] = safe_div(df[rg["high"]] - df[rg["low"]], df[ANCHOR])
        built.append(rg["out"])


def add_realized_vol(df: pd.DataFrame, horizon: str, spec: dict, built: list[str]) -> None:
    """Rolling standard deviation of returns per ticker. Returns are already in percent
    points, so this is not rescaled."""
    rv = spec["rvol"]
    if has(df, rv["ret"], "ticker"):
        window = REALIZED_VOL_WINDOW[horizon]
        min_periods = max(2, window // 2)
        df[rv["out"]] = (
            df.groupby("ticker")[rv["ret"]]
              .transform(lambda s: s.rolling(window, min_periods=min_periods).std())
        )
        built.append(rv["out"])


def add_cyclical(df: pd.DataFrame, spec: dict, built: list[str]) -> None:
    """Cyclical (sine and cosine) encodings of day-of-week and month-of-year."""
    if "Date" not in df.columns:
        return
    date = pd.to_datetime(df["Date"], errors="coerce")
    if "dow" in spec["cyclical"]:
        dow = date.dt.dayofweek
        df["dow_sin"] = np.sin(2 * np.pi * dow / 5.0)
        df["dow_cos"] = np.cos(2 * np.pi * dow / 5.0)
        built.extend(["dow_sin", "dow_cos"])
    if "month" in spec["cyclical"]:
        month = date.dt.month
        df["month_sin"] = np.sin(2 * np.pi * month / 12.0)
        df["month_cos"] = np.cos(2 * np.pi * month / 12.0)
        built.extend(["month_sin", "month_cos"])


def add_days_to_close(df: pd.DataFrame, spec: dict, built: list[str]) -> None:
    """Trading days remaining until the candle closes, as a fraction. Drives confidence:
    more days left means more uncertainty. Daily has none (always a full next-day candle).
    Uses a business-day approximation that ignores market holidays until a real trading
    calendar is wired in."""
    name = spec["days_to_close"]
    if name is None or "Date" not in df.columns:
        return
    date = pd.to_datetime(df["Date"], errors="coerce")

    if name == "days_to_close_weekly":
        remaining = (4 - date.dt.dayofweek).clip(lower=0)
        df[name] = (remaining / TRADING_DAYS["weekly"]).clip(0, 1)
    elif name == "days_to_close_monthly":
        month_end = date + MonthEnd(0)
        start = (date + pd.Timedelta(days=1)).values.astype("datetime64[D]")
        end = (month_end + pd.Timedelta(days=1)).values.astype("datetime64[D]")
        remaining = np.busday_count(start, end)
        df[name] = np.clip(remaining / TRADING_DAYS["monthly"], 0, 1)
    built.append(name)


# ----------------------------------------------------------------------------------
# Label building (the only place allowed to look forward)
# ----------------------------------------------------------------------------------
def period_id(date: pd.Series, horizon: str) -> pd.Series:
    """Candle identifier per horizon: ISO year-week for weekly, year-month for monthly."""
    date = pd.to_datetime(date, errors="coerce")
    if horizon == "weekly":
        iso = date.dt.isocalendar()
        return (iso["year"].astype(int) * 100 + iso["week"].astype(int))
    if horizon == "monthly":
        return (date.dt.year * 100 + date.dt.month)
    return pd.Series(np.arange(len(date)), index=date.index)  # daily: every row its own


def build_label(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    """
    Attach target_<horizon> in percent points. For daily it is the next day's move.
    For weekly and monthly it is the move from the row's anchor to the candle's closing
    anchor (the in-progress candle's outcome). Rows that cannot form a complete label
    are dropped.
    """
    target = config.target_column(horizon)
    if ANCHOR not in df.columns:
        print(f"[features] {horizon}: no anchor close, cannot build {target}")
        df[target] = np.nan
        return df

    df = df.sort_values(["ticker", "Date"]).reset_index(drop=True)

    if horizon == "daily":
        next_anchor = df.groupby("ticker")[ANCHOR].shift(-1)
        df[target] = (next_anchor / df[ANCHOR] - 1.0) * 100.0
    else:
        df["_period"] = period_id(df["Date"], horizon)
        period_close = df.groupby(["ticker", "_period"])[ANCHOR].transform("last")
        df[target] = (period_close / df[ANCHOR] - 1.0) * 100.0
        # Drop the final (possibly open) candle per ticker: its close is not realized yet.
        last_period = df.groupby("ticker")["_period"].transform("max")
        df = df[df["_period"] < last_period].copy()
        df = df.drop(columns="_period")

    df = df.dropna(subset=[target]).reset_index(drop=True)
    return df


# ----------------------------------------------------------------------------------
# Per-horizon orchestration
# ----------------------------------------------------------------------------------
def engineer_horizon(df: pd.DataFrame, horizon: str) -> tuple[pd.DataFrame, list[str]]:
    """Engineer all features for one horizon and return the table plus the model columns."""
    spec = HORIZON_SPEC[horizon]
    key = spec["key"]
    built: list[str] = []

    add_distance_features(df, key, built)
    add_bollinger_features(df, key, built)
    add_relative_volume(df, spec, built)
    add_range_pct(df, spec, built)
    add_realized_vol(df, horizon, spec, built)
    add_cyclical(df, spec, built)
    add_days_to_close(df, spec, built)

    df = build_label(df, horizon)

    # Model feature set: engineered features plus the raw passthrough columns present.
    passthrough = [c for c in spec["passthrough"] if c in df.columns]
    model_features = built + passthrough

    # Final table: shared keys + ticker (categorical feature) + model features + label.
    target = config.target_column(horizon)
    keep = ["Date", "ticker"] + model_features + [target]
    keep = [c for c in dict.fromkeys(keep) if c in df.columns]  # de-dupe, preserve order
    out = df[keep].copy()

    # Drop warm-up and any remaining NaN rows in the present model features.
    present_features = [c for c in model_features if c in out.columns]
    out = out.dropna(subset=present_features + [target]).reset_index(drop=True)
    return out, model_features


def run() -> None:
    """Engineer features and the label for every horizon and persist the results."""
    report_dir = plotting.prepare_results_dir("tables", "feature_engineering")

    for horizon in HORIZONS:
        raw = io_store.read_raw(horizon)
        engineered, model_features = engineer_horizon(raw, horizon)

        io_store.write_features(engineered, horizon)
        pd.Series(model_features, name="model_feature").to_csv(
            report_dir / f"{horizon}_features.csv", index=False
        )
        print(f"[features] {horizon}: {len(model_features)} model features, "
              f"{len(engineered)} rows -> stored")

    print("[features] done")


if __name__ == "__main__":
    run()
