"""Public API — the ONLY surface the CLI is allowed to import."""
from __future__ import annotations


def market_snapshot() -> dict:
    """Indices + last-close direction/% (+ optional FX) for the guest screen."""
    raise NotImplementedError


def sync_if_needed() -> dict:
    """Run the smart sync; return a summary of what was updated."""
    raise NotImplementedError


def predict(index: str, horizon: str, amount: float | None = None,
            currency: str | None = None) -> dict:
    """
    Returns:
        {
          "low": float, "high": float, "confidence": float,   # % move range
          "recommendation": "long" | "short" | "stay_out",
          "profit_range": (low, high) | None                  # if amount given
        }
    """
    raise NotImplementedError


def get_series(index: str, horizon: str):
    """Price series up to last close, for the chart widget."""
    raise NotImplementedError


def register(first, last, email, password): raise NotImplementedError
def login(email, password): raise NotImplementedError
def update_profile(user_id, **changes): raise NotImplementedError
