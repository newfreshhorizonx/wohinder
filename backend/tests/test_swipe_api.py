"""Tests for the swipe app API (M4): feed, swipes and the Anfrage preview. Run: pytest"""

import pytest
from fastapi.testclient import TestClient

from app.anfrage import MISSING_EMAIL, anfrage_for
from app.main import app, swipes
from app.models import HousingType

from .test_core import make_listing, make_profile

client = TestClient(app)  # calls the API in-process, no server needed

PROFILE = "souissinebilai"


@pytest.fixture(autouse=True)
def fresh_swipes():
    """autouse: runs around every test in this file, so each starts with no swipes."""
    swipes._swipes.clear()
    yield
    swipes._swipes.clear()


def feed_ids(profile_id: str = PROFILE) -> list[str]:
    response = client.get(f"/profiles/{profile_id}/feed")
    assert response.status_code == 200
    return [card["listing"]["id"] for card in response.json()]


# --- Feed --------------------------------------------------------------------

def test_feed_is_sorted_best_first():
    totals = [card["score"]["total"] for card in client.get(f"/profiles/{PROFILE}/feed").json()]
    assert totals, "feed should not be empty"
    assert totals == sorted(totals, reverse=True)


def test_feed_leaves_out_rejected_listings():
    # fake-8 costs 720 €, far over both personal budgets
    assert "fake-8" not in feed_ids("souissinebilai")
    assert "fake-8" not in feed_ids("newfreshhorizonx")


def test_whole_flat_only_shows_up_for_team():
    assert "fake-12" in feed_ids("team")
    assert "fake-12" not in feed_ids("souissinebilai")


def test_unknown_profile_is_404():
    assert client.get("/profiles/nobody/feed").status_code == 404


# --- Swipes ------------------------------------------------------------------

def test_right_swipe_returns_anfrage_and_removes_card():
    response = client.post(f"/profiles/{PROFILE}/swipes",
                           json={"listing_id": "fake-2", "direction": "right"})
    assert response.status_code == 200
    anfrage = response.json()["anfrage"]
    assert anfrage.startswith("Sehr geehrte Frau Becker,")
    assert "fake-2" not in feed_ids()


def test_left_swipe_has_no_anfrage():
    response = client.post(f"/profiles/{PROFILE}/swipes",
                           json={"listing_id": "fake-1", "direction": "left"})
    assert response.json()["anfrage"] is None
    assert "fake-1" not in feed_ids()


def test_swipes_are_listed_and_can_be_reset():
    client.post(f"/profiles/{PROFILE}/swipes", json={"listing_id": "fake-1", "direction": "left"})
    assert client.get(f"/profiles/{PROFILE}/swipes").json() == [
        {"listing_id": "fake-1", "direction": "left"}]
    client.delete(f"/profiles/{PROFILE}/swipes")
    assert "fake-1" in feed_ids()


def test_swipes_are_per_profile():
    client.post(f"/profiles/{PROFILE}/swipes", json={"listing_id": "fake-1", "direction": "left"})
    assert "fake-1" in feed_ids("newfreshhorizonx")


def test_unknown_listing_is_404():
    response = client.post(f"/profiles/{PROFILE}/swipes",
                           json={"listing_id": "nope", "direction": "right"})
    assert response.status_code == 404


def test_invalid_direction_is_422():
    # 422 = "Unprocessable Entity": pydantic rejected the request body
    response = client.post(f"/profiles/{PROFILE}/swipes",
                           json={"listing_id": "fake-1", "direction": "up"})
    assert response.status_code == 422


# --- Anfrage text ------------------------------------------------------------

def test_anfrage_uses_du_for_first_name():
    text = anfrage_for(make_listing(contact_name="Lena", title="Zimmer"), make_profile())
    assert text.startswith("Hallo Lena,")
    assert "deine Anzeige" in text and "Du erreichst mich" in text


def test_anfrage_uses_ihr_for_wg():
    listing = make_listing(contact_name="", housing_type=HousingType.WG_3)
    text = anfrage_for(listing, make_profile())
    assert "eure Anzeige" in text and "Ihr erreicht mich" in text


def test_anfrage_uses_wir_for_team():
    team = make_profile(members=["a", "b"])
    text = anfrage_for(make_listing(contact_name="Frau Müller"), team)
    assert "wir haben Ihre Anzeige" in text and "erreichen uns" in text


def test_anfrage_contact_details():
    without = anfrage_for(make_listing(), make_profile())
    assert MISSING_EMAIL in without
    with_contact = anfrage_for(make_listing(), make_profile(
        contact_email="test@example.org", contact_phone="0151 000000"))
    assert "test@example.org oder telefonisch unter 0151 000000" in with_contact
    assert with_contact.rstrip().endswith("Test")  # signed with display_name


# --- PWA ---------------------------------------------------------------------

def test_root_redirects_to_app():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/app/"
