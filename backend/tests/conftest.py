"""Shared test setup. pytest loads this file automatically before the tests."""

import pytest

from app import main


@pytest.fixture(autouse=True)
def empty_listing_db(tmp_path, monkeypatch):
    """Every test gets its own empty listing database, never the real data/ one.

    tmp_path: a fresh temporary folder per test (built into pytest).
    monkeypatch: changes a variable for one test and puts it back afterwards.
    """
    db = tmp_path / "listings.sqlite"
    monkeypatch.setattr(main, "LISTING_DB", db)
    return db
