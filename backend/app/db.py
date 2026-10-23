"""SQLite storage for listings. One file in data/ (gitignored), no server needed."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Listing
from .profiles import REPO_ROOT

DEFAULT_DB = REPO_ROOT / "data" / "wohinder.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id         TEXT PRIMARY KEY,  -- "<source>:<id on the site>", the dedup key
    source     TEXT NOT NULL,
    url        TEXT NOT NULL,
    title      TEXT NOT NULL,
    data       TEXT NOT NULL,     -- the full Listing as JSON
    first_seen TEXT NOT NULL
);

-- Small key/value table, e.g. the last email UID we imported
CREATE TABLE IF NOT EXISTS state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class ListingStore:
    """Saves listings and skips ones we already have.

    Pass ":memory:" as path for a throwaway database (used in tests).
    """

    def __init__(self, path: Path | str = DEFAULT_DB) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    def add(self, listing: Listing) -> bool:
        """Insert a listing. Returns False if it was already stored (duplicate)."""
        # `with self.conn` commits on success and rolls back on an exception.
        with self.conn:
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO listings (id, source, url, title, data, first_seen) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (listing.id, listing.source, listing.url, listing.title,
                 listing.model_dump_json(), datetime.now(timezone.utc).isoformat()),
            )
        return cursor.rowcount == 1

    def all(self) -> list[Listing]:
        """All listings, newest first."""
        rows = self.conn.execute("SELECT data FROM listings ORDER BY first_seen DESC, rowid DESC")
        return [Listing.model_validate_json(data) for (data,) in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]

    def get_state(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_state(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO state (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def close(self) -> None:
        self.conn.close()
