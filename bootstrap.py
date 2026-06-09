"""One-time bootstrap: pull historical data, build features, and train every model.

Run ONCE before the first launch (and again only after a very long gap if you prefer a
clean full retrain instead of incremental catch-up):

    python bootstrap.py

After this, `streamlit run cli/app.py` handles everything incrementally on each launch.
"""
from __future__ import annotations

# from backend import api
# from ai.training.train import train
# import yaml


def main() -> None:
    """
    1. Load config/settings.yaml (tickers, history_start, horizons, ...).
    2. Pull full history for every index and build the feature table (backend).
    3. For each (index, horizon): train a model and save it to ai/artifacts/.
    4. Stamp meta.last_sync_at so the routine run knows where to resume.
    TODO: implement once backend + ai stubs are filled in.
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
