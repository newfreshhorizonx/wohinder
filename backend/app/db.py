"""Storage for listings, swipes and small bits of state.

Locally this is one SQLite file in data/ (gitignored). In the cloud (Vercel)
the files don't survive, so DATABASE_URL points at a Postgres database instead.
The SQL below works on both.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Listing
from .profiles import REPO_ROOT

DEFAULT_DB = REPO_ROOT / "data" / "wohinder.sqlite"

# {auto_id} differs per database: an integer that counts up by itself.
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS listings (
        id         TEXT PRIMARY KEY,  -- "<source>:<id on the site>", the dedup key
        source     TEXT NOT NULL,
        url        TEXT NOT NULL,
        title      TEXT NOT NULL,
        data       TEXT NOT NULL,     -- the full Listing as JSON
        first_seen TEXT NOT NULL
    )""",
    # Small key/value table, e.g. the last email UID we imported
    """CREATE TABLE IF NOT EXISTS state (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS swipes (
        seq        {auto_id},         -- order of the swipes, newest = highest
        profile_id TEXT NOT NULL,
        listing_id TEXT NOT NULL,
        direction  TEXT NOT NULL,
        UNIQUE (profile_id, listing_id)
    )""",
]
AUTO_ID = {"sqlite": "INTEGER PRIMARY KEY AUTOINCREMENT", "postgres": "BIGSERIAL PRIMARY KEY"}


def default_target() -> Path | str:
    """Where the data lives: DATABASE_URL if set (cloud), else the local file."""
    return os.environ.get("DATABASE_URL") or DEFAULT_DB


class Database:
    """A connection to SQLite or Postgres with one execute() for both.

    Pass ":memory:" for a throwaway SQLite database (used in tests).
    """

    def __init__(self, target: Path | str | None = None) -> None:
        target = default_target() if target is None else target
        self.postgres = str(target).startswith(("postgres://", "postgresql://"))
        if self.postgres:
            import psycopg   # only needed in the cloud, so imported only here
            # autocommit: every statement is saved right away, no commit() needed
            self.conn = psycopg.connect(str(target), autocommit=True)
        else:
            if target != ":memory:":
                Path(target).parent.mkdir(parents=True, exist_ok=True)
            # isolation_level=None is sqlite3's name for autocommit
            self.conn = sqlite3.connect(target, isolation_level=None)
        auto_id = AUTO_ID["postgres" if self.postgres else "sqlite"]
        for statement in SCHEMA:
            self.execute(statement.format(auto_id=auto_id))

    def execute(self, sql: str, params: tuple = ()):
        """Run one statement. Write SQL with ? placeholders; Postgres wants %s."""
        if self.postgres:
            sql = sql.replace("?", "%s")
        return self.conn.execute(sql, params)

    def close(self) -> None:
        self.conn.close()


class ListingStore:
    """Saves listings and skips ones we already have."""

    def __init__(self, target: Path | str | None = None) -> None:
        self.db = Database(target)

    def add(self, listing: Listing) -> bool:
        """Insert a listing. Returns False if it was already stored (duplicate)."""
        cursor = self.db.execute(
            "INSERT INTO listings (id, source, url, title, data, first_seen) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO NOTHING",
            (listing.id, listing.source, listing.url, listing.title,
             listing.model_dump_json(), datetime.now(timezone.utc).isoformat()),
        )
        return cursor.rowcount == 1

    def all(self) -> list[Listing]:
        """All listings, newest first."""
        rows = self.db.execute("SELECT data FROM listings ORDER BY first_seen DESC, id DESC")
        return [Listing.model_validate_json(data) for (data,) in rows]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM listings").fetchone()[0]

    def get_state(self, key: str, default: str | None = None) -> str | None:
        row = self.db.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_state(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO state (key, value) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def close(self) -> None:
        self.db.close()
