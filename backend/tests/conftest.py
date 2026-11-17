"""Shared test setup. pytest loads this file automatically before the tests."""

import pytest

from app import main


@pytest.fixture(autouse=True)
def empty_listing_db(tmp_path, monkeypatch):
    """Every test gets its own empty database (listings and swipes), never the real one.

    tmp_path: a fresh temporary folder per test (built into pytest).
    monkeypatch: changes a variable for one test and puts it back afterwards.
    """
    # Cloud settings from .env must not leak into tests
    for name in ("DATABASE_URL", "APP_PASSWORD", "IMPORT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    db = tmp_path / "listings.sqlite"
    monkeypatch.setattr(main, "LISTING_DB", db)
    return db
