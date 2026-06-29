"""
Build the final production models (stage 3).

For each horizon this unifies the train and test splits into the full dataset and refits
the three quantile boosters on all of it, so the shipped models use every available row.
The boosters and a metadata file are written to Inference_models/, one subfolder per
horizon, which is what the predictor and the backend load at inference time.

This is a full retrain. There is no continued training: when new data arrives, this stage
runs again from scratch. The metadata records last_trained_through per horizon.
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

import datetime as dt
import json

import pandas as pd

import config
from utils import io_store, modeling

# ----------------------------------------------------------------------------------
# GLOBAL PARAMETERS
# ----------------------------------------------------------------------------------
HORIZONS = config.HORIZONS


def rounds_for(horizon: str, qname: str) -> int:
    """Reuse the boosting-round count chosen during development cross-validation if
    available, otherwise fall back to the configured maximum."""
    cv_path = config.RESULTS_ROOT / "metrics" / f"train_{horizon}" / qname / "cv_summary.json"
    if cv_path.exists():
        try:
            return int(json.loads(cv_path.read_text())["rounds_used"])
        except Exception:
            pass
    return int(modeling.HORIZON_PARAMS[horizon]["n_estimators"])


def build_horizon(horizon: str) -> None:
    """Refit and persist the three quantile boosters for one horizon on all data."""
    target = config.target_column(horizon)
    train_df = io_store.read_split(horizon, "train")
    test_df = io_store.read_split(horizon, "test")
    full = pd.concat([train_df, test_df], ignore_index=True)

    feature_cols = modeling.get_feature_columns(full, target)
    last_through = str(pd.to_datetime(full["Date"]).max().date()) if "Date" in full else None

    for qname, alpha in config.QUANTILES.items():
        booster = modeling.fit_full(full, horizon, alpha, feature_cols, target,
                                    rounds_for(horizon, qname))
        booster.save_model(str(config.inference_model_path(horizon, qname)))

    metadata = {
        "horizon": horizon,
        "feature_columns": feature_cols,
        "tickers": config.TICKERS,
        "quantiles": config.QUANTILES,
        "nominal_coverage": config.NOMINAL_COVERAGE,
        "n_rows": int(len(full)),
        "last_trained_through": last_through,
        "built_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    config.inference_metadata_path(horizon).write_text(json.dumps(metadata, indent=2))

    print(f"[final-build] {horizon}: refit on {len(full)} rows, "
          f"through {last_through} -> Inference_models/{horizon}/")


def run() -> None:
    """Build production models for every horizon."""
    for horizon in HORIZONS:
        build_horizon(horizon)
    print("[final-build] done")


if __name__ == "__main__":
    run()
