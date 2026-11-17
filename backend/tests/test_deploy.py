"""Tests for what the cloud version needs: login, import endpoint, saved swipes."""

from fastapi.testclient import TestClient

from app import main
from app.db import ListingStore
from app.swipes import Swipe, SwipeStore

from .test_email_import import WG_REAL_HTML, FakeInbox, make_alert

client = TestClient(main.app)


# --- Login ---------------------------------------------------------------------

def test_without_password_the_app_is_open():
    assert client.get("/profiles").status_code == 200


def test_password_locks_api_and_app(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "geheim-123")
    fresh = TestClient(main.app)   # no cookies yet
    assert fresh.get("/profiles").status_code == 401
    page = fresh.get("/app/", follow_redirects=False)
    assert page.status_code == 307 and page.headers["location"] == "/login"
    assert "Passwort" in fresh.get("/login").text


def test_wrong_password_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "geheim-123")
    monkeypatch.setattr(main.asyncio, "sleep", _no_sleep)
    fresh = TestClient(main.app)
    response = fresh.post("/login", data={"password": "falsch"})
    assert response.status_code == 401
    assert "Falsches Passwort" in response.text
    assert fresh.get("/profiles").status_code == 401


def test_right_password_sets_cookie(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "geheim-123")
    fresh = TestClient(main.app)
    response = fresh.post("/login", data={"password": "geheim-123"}, follow_redirects=False)
    assert response.status_code == 303
    assert "geheim-123" not in response.headers["set-cookie"]   # only a hash
    assert fresh.get("/profiles").status_code == 200           # cookie is kept


async def _no_sleep(seconds):
    pass


# --- Import endpoint -------------------------------------------------------------

def test_import_needs_the_secret(monkeypatch):
    monkeypatch.setenv("IMPORT_SECRET", "s3cret")
    assert client.post("/api/import").status_code == 401
    assert client.post("/api/import", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_import_without_configured_secret_is_refused():
    assert client.post("/api/import", headers={"Authorization": "Bearer "}).status_code == 401


def test_import_endpoint_imports(monkeypatch, empty_listing_db):
    monkeypatch.setenv("IMPORT_SECRET", "s3cret")
    monkeypatch.setenv("APP_PASSWORD", "geheim-123")   # import works without login

    class FakeInboxContext(FakeInbox):
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            pass

    monkeypatch.setattr(main, "Inbox", lambda: FakeInboxContext([make_alert(uid=8, html=WG_REAL_HTML)]))
    response = client.post("/api/import", headers={"Authorization": "Bearer s3cret"})
    assert response.status_code == 200
    assert response.json()["new"] == 2
    assert ListingStore(empty_listing_db).count() == 2


# --- Swipes are stored in the database -------------------------------------------

def test_swipes_survive_a_new_connection(empty_listing_db):
    first = SwipeStore(empty_listing_db)
    first.record("team", Swipe(listing_id="a", direction="right"))
    first.record("team", Swipe(listing_id="b", direction="left"))
    first.record("team", Swipe(listing_id="c", direction="right"))
    first.close()

    second = SwipeStore(empty_listing_db)   # like a server restart
    assert second.swiped_ids("team") == {"a", "b", "c"}
    assert second.right_ids("team") == ["c", "a"]
    assert second.swiped_ids("souissinebilai") == set()
