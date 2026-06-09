"""Smart sync: figure out how many candles we missed and update ONLY those."""
from __future__ import annotations
from datetime import datetime


def missed_periods(last_sync_at: datetime, now: datetime) -> dict:
    """
    Using a trading calendar (and the ~01:00 Israel-time cutoff), return how many
    daily / weekly / monthly candles closed since last_sync_at.
    e.g. {"daily": 5, "weekly": 1, "monthly": 0}
    TODO: implement with pandas-market-calendars.
    """
    raise NotImplementedError


def sync_if_needed(now: datetime | None = None) -> dict:
    """
    1. read last_sync_at from DB
    2. missed = missed_periods(...)
    3. fetch only missing candles, recompute affected features, update last_sync_at
    4. if nothing missing -> return early (no wasted calls)
    Returns a summary of what was updated (also fed to the AI incremental step).
    """
    raise NotImplementedError
