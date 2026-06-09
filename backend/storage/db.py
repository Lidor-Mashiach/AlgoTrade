"""SQLite access: candles, features, users, meta(last_sync_at)."""
from __future__ import annotations
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    first_name TEXT, last_name TEXT,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL   -- bcrypt hash, never plaintext
);
CREATE TABLE IF NOT EXISTS candles (
    ticker TEXT, horizon TEXT, date TEXT,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (ticker, horizon, date)
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);  -- e.g. last_sync_at
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn
