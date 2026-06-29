"""
Global configuration for the Algo-Trade AI module.

This is the single source of truth for cross-cutting constants used by every stage
of the pipeline (data extraction, feature engineering, splitting, training, evaluation,
and inference). File-specific knobs still live at the top of each script, but anything
shared across files is defined here so the values never drift apart.

Nothing in this file pulls data or trains a model. It only declares constants and paths.
"""

from __future__ import annotations

import pathlib

# ----------------------------------------------------------------------------------
# Paths (all absolute, derived from this file's location so the pipeline is CWD-safe)
# ----------------------------------------------------------------------------------
AI_ROOT = pathlib.Path(__file__).resolve().parent

DATA_STORE_DIR = AI_ROOT / "data_store"      # intermediate DataFrames that flow between folders
RAW_DIR = DATA_STORE_DIR / "raw"             # per-horizon raw tables (after pooling and suffix split)
FEATURES_DIR = DATA_STORE_DIR / "features"   # per-horizon engineered tables (features + label)
SPLITS_DIR = DATA_STORE_DIR / "splits"       # per-horizon train/test parquet files

INFERENCE_MODELS_DIR = AI_ROOT / "Inference_models"  # final production boosters that ship
DEV_MODELS_DIR = AI_ROOT / "dev_models"      # stage-2 development boosters (diagnostic)
RESULTS_ROOT = AI_ROOT / "results"           # plots, reports, metrics, tables; latest run only

# Placeholder for the backend per-ticker raw store. No real file exists yet, so the
# data-access function in PreTraining/Data-Extraction reads from here as a template and
# raises a clear error if a ticker table is missing. Wire this to the backend later.
TEMPLATE_DATA_DIR = DATA_STORE_DIR / "backend_template"

# ----------------------------------------------------------------------------------
# Universe and model layout
# ----------------------------------------------------------------------------------
# Pooled indices only. Single stocks and meme stocks are intentionally excluded
# because pooling assumes homogeneous, index-like dynamics.
TICKERS = ["SPY", "QQQ", "TA35", "TA125", "DAX", "DJI"]

HORIZONS = ["daily", "weekly", "monthly"]

# Quantile name -> alpha passed to the LightGBM pinball loss. This alpha is the ONLY
# thing that differs between the three boosters of a horizon. The label is a single
# real value shared by all three.
QUANTILES = {"q10": 0.10, "q50": 0.50, "q90": 0.90}

# Nominal interval coverage implied by the band [Q10, Q90]. Used by evaluation to
# compare realized coverage against the target. Acceptable realized range is 80-85%.
NOMINAL_COVERAGE = 0.80

# ----------------------------------------------------------------------------------
# History depth per horizon (start date of training data)
# ----------------------------------------------------------------------------------
# Daily and weekly start around 2010 (older daily data is noisier). Monthly reaches
# as far back as possible so the model can see crash events (2000, 2008) that teach
# the lower tail (Q10).
HISTORY_START = {
    "daily": "2010-01-01",
    "weekly": "2010-01-01",
    "monthly": "1993-01-01",
}

# ----------------------------------------------------------------------------------
# Indicator parameters and conventions (must match the backend extractor exactly)
# ----------------------------------------------------------------------------------
MA_PERIODS = [20, 50, 100, 150, 200]   # SMA and EMA periods
BB_PERIOD = 20                          # Bollinger period (base is the 20-period SMA)
BB_K = 2.0                              # Bollinger band width in sigma
RSI_LENGTH = 14                         # Wilder RSI length
VOLUME_AVG_WINDOW = 90                  # window behind volume_avg_daily_90

# Rolling window (in rows) for realized volatility per horizon.
# IMPORTANT: every pct_change_* column is already in percentage points (times 100),
# so realized volatility must NOT be multiplied by 100 again.
REALIZED_VOL_WINDOW = {"daily": 21, "weekly": 13, "monthly": 12}

# Approximate number of trading days inside a candle, used for the days_to_close
# fraction. Daily has no time_to_close because it always forecasts a full next-day candle.
TRADING_DAYS_PER_CANDLE = {"weekly": 5, "monthly": 21}

# ----------------------------------------------------------------------------------
# Splitting and cross-validation
# ----------------------------------------------------------------------------------
# Fraction of each ticker's candle groups held out for the final test set. Held out
# per ticker and time-ordered, so every index is represented in proportion and the
# test period is the most recent (no look-ahead).
TEST_SIZE = 0.20

# Number of GroupKFold folds used for validation and tuning on the train set.
# Lidor's call: 5 or 6. Groups are whole candles, so no candle straddles a fold.
N_SPLITS = 5

# Embargo gap (in candle groups) between folds. Adjacent candles share long look-back
# windows, so a strict setup would leave a small gap between train and validation.
# Disabled by default for this course project. Flagged as a future improvement.
EMBARGO_GROUPS = 0

# ----------------------------------------------------------------------------------
# Reproducibility and plotting
# ----------------------------------------------------------------------------------
RANDOM_SEED = 42
PLOT_DPI = 130

# ----------------------------------------------------------------------------------
# Helper column names (used only to build the label, never fed to the model)
# ----------------------------------------------------------------------------------
# The current daily close at each row's date. It is the universal anchor for both the
# label denominator ("last known daily close") and the relative feature engineering
# (the running close, consistent with the intra-candle convention). Dropped before training.
ANCHOR_CLOSE = "anchor_close_daily"

# Shared columns carried into every horizon dataset.
SHARED_COLUMNS = ["Date", "ticker", ANCHOR_CLOSE]

# Column name of the regression label per horizon. Expressed in percentage points
# (for example 1.5 means a +1.5% move), to match the scale of the pct_change features.
def target_column(horizon: str) -> str:
    """Return the label column name for a horizon, for example 'target_daily'."""
    return f"target_{horizon}"


# ----------------------------------------------------------------------------------
# Model path helpers (pure path construction, no heavy imports)
# ----------------------------------------------------------------------------------
def dev_model_path(horizon: str, qname: str) -> pathlib.Path:
    """Stage-2 development booster path: dev_models/<horizon>/<quantile>.txt."""
    path = DEV_MODELS_DIR / horizon / f"{qname}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def inference_model_path(horizon: str, qname: str) -> pathlib.Path:
    """Final production booster path: Inference_models/<horizon>/<quantile>.txt."""
    path = INFERENCE_MODELS_DIR / horizon / f"{qname}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def inference_metadata_path(horizon: str) -> pathlib.Path:
    """Production metadata path: Inference_models/<horizon>/metadata.json."""
    path = INFERENCE_MODELS_DIR / horizon / "metadata.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
