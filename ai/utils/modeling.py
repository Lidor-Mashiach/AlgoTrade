"""
Shared modeling code.

The pieces of training that both stage 2 (Train) and stage 3 (Production-FinalTraining)
need live here, so neither stage has to import the other. That includes the per-horizon
hyperparameters and the low-level fit helpers (feature selection, the categorical ticker,
sample weighting, and a full fit). The stage-2 specifics (cross-validation, plots, saving
development models) stay inside the Train folder.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config

GROUP_COLUMN = "group_id"
NON_FEATURE_COLS = ["Date", GROUP_COLUMN]

# ----------------------------------------------------------------------------------
# Hyperparameters (per horizon, shared by the three quantiles of that horizon)
# ----------------------------------------------------------------------------------
# All three quantile boosters of a horizon share these settings. Only the pinball alpha
# differs, and it is set at fit time. Monthly carries the heaviest regularization because
# it has the least data and the longest memory.
_BASE = {
    "boosting_type": "gbdt",
    "n_estimators": 600,
    "learning_rate": 0.03,
    "num_leaves": 31,
    "max_depth": -1,
    "min_child_samples": 40,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "min_split_gain": 0.0,
    "random_state": config.RANDOM_SEED,
    "verbosity": -1,
}


def _with(**overrides) -> dict:
    """Return a copy of the baseline with the given keys overridden."""
    params = dict(_BASE)
    params.update(overrides)
    return params


HORIZON_PARAMS = {
    "daily": _with(),
    "weekly": _with(
        n_estimators=500,
        learning_rate=0.025,
        num_leaves=24,
        max_depth=6,
        min_child_samples=60,
        reg_lambda=2.0,
    ),
    "monthly": _with(
        n_estimators=400,
        learning_rate=0.02,
        num_leaves=15,
        max_depth=4,
        min_child_samples=80,
        subsample=0.7,
        colsample_bytree=0.7,
        reg_alpha=0.5,
        reg_lambda=5.0,
    ),
}

# Stop boosting after this many rounds without validation improvement.
EARLY_STOPPING_ROUNDS = 50


# ----------------------------------------------------------------------------------
# Feature frame and weights
# ----------------------------------------------------------------------------------
def get_feature_columns(df: pd.DataFrame, target: str) -> list[str]:
    """Model feature columns: everything except Date, the label, and the group id.
    The ticker column stays, as a categorical feature."""
    return [c for c in df.columns if c not in NON_FEATURE_COLS + [target]]


def to_model_frame(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Build the feature frame with ticker as a fixed-category dtype, so train, test, and
    inference all share the same category mapping."""
    X = df[feature_cols].copy()
    if "ticker" in X.columns:
        X["ticker"] = pd.Categorical(X["ticker"], categories=config.TICKERS)
    return X


def make_sample_weight(df: pd.DataFrame) -> np.ndarray:
    """Balanced per-ticker weights: under-represented indices are up-weighted so a long
    history does not dominate a short one."""
    if "ticker" not in df.columns:
        return np.ones(len(df))
    counts = df["ticker"].value_counts()
    n_tickers = len(counts)
    weights = df["ticker"].map(lambda t: len(df) / (n_tickers * counts[t]))
    return weights.to_numpy()


# ----------------------------------------------------------------------------------
# LightGBM helpers
# ----------------------------------------------------------------------------------
def build_params(horizon: str, alpha: float, device: str) -> dict:
    """Assemble the LightGBM parameter dict for one horizon and one quantile."""
    params = dict(HORIZON_PARAMS[horizon])
    params["objective"] = "quantile"
    params["alpha"] = alpha
    params["metric"] = "quantile"
    params["device"] = device
    return params


def make_dataset(X: pd.DataFrame, y: np.ndarray, w: np.ndarray):
    """Wrap a feature frame in a LightGBM Dataset with ticker as a categorical feature."""
    import lightgbm as lgb
    return lgb.Dataset(
        X, label=y, weight=w,
        categorical_feature=["ticker"] if "ticker" in X.columns else "auto",
        free_raw_data=False,
    )


def fit_full(train_df: pd.DataFrame, horizon: str, alpha: float,
             feature_cols: list[str], target: str, num_boost_round: int):
    """Fit one quantile on an entire frame for a fixed number of rounds (no early stop).
    Used by stage 2 for the development model and by stage 3 for the production model."""
    import lightgbm as lgb
    from utils import gpu

    device = gpu.resolve_lgbm_device()
    params = build_params(horizon, alpha, device)
    params.pop("n_estimators", None)

    X = to_model_frame(train_df, feature_cols)
    y = train_df[target].to_numpy()
    w = make_sample_weight(train_df)
    dtrain = make_dataset(X, y, w)
    return lgb.train(params, dtrain, num_boost_round=max(1, num_boost_round),
                     callbacks=[lgb.log_evaluation(0)])
