"""Tests for greeting detection, scoring and profile loading. Run: pytest"""

from datetime import date

from app.greeting import greeting_for
from app.models import HousingType, Listing, Location, Profile
from app.profiles import load_profiles
from app.scoring import distance_km, score

HDA = Location(name="h_da", lat=49.8668, lon=8.6383)


def make_profile(**overrides) -> Profile:
    data = dict(
        id="test", display_name="Test", members=["test"],
        housing_types=[HousingType.EINZELZIMMER, HousingType.WG_3],
        max_warmmiete=500, min_size_m2=12, radius_km=5, center=HDA,
        move_in_from=date(2026, 12, 1), about_me="", study="Informatik",
    )
    data.update(overrides)
    return Profile(**data)


def make_listing(**overrides) -> Listing:
    data = dict(id="1", source="wg-gesucht", url="https://example.org/1", title="Zimmer")
    data.update(overrides)
    return Listing(**data)


# --- Greeting ----------------------------------------------------------------

def test_greeting_frau():
    assert greeting_for(make_listing(contact_name="Frau Müller")) == "Sehr geehrte Frau Müller,"


def test_greeting_herr_abbreviation():
    assert greeting_for(make_listing(contact_name="Hr. Schmidt")) == "Sehr geehrter Herr Schmidt,"


def test_greeting_wg_by_name():
    assert greeting_for(make_listing(contact_name="WG Kranichstein")) == "Hallo liebe WG,"


def test_greeting_wg_by_type():
    listing = make_listing(contact_name="", housing_type=HousingType.WG_3)
    assert greeting_for(listing) == "Hallo liebe WG,"


def test_greeting_first_name():
    assert greeting_for(make_listing(contact_name="Lena")) == "Hallo Lena,"


def test_greeting_company():
    listing = make_listing(contact_name="Musterbau Immobilien GmbH")
    assert greeting_for(listing) == "Sehr geehrte Damen und Herren,"


def test_greeting_unknown():
    assert greeting_for(make_listing()) == "Hallo,"


# --- Scoring -----------------------------------------------------------------

def test_distance_darmstadt_frankfurt_is_about_25km():
    assert 24 < distance_km(49.8728, 8.6512, 50.1109, 8.6821) < 28


def test_perfect_listing_scores_high():
    listing = make_listing(housing_type=HousingType.EINZELZIMMER, warmmiete=330,
                           size_m2=16, lat=49.870, lon=8.645,
                           available_from=date(2026, 12, 15))
    result = score(listing, make_profile())
    assert not result.rejected
    assert result.total >= 95


def test_wrong_type_is_rejected():
    listing = make_listing(housing_type=HousingType.WOHNUNG_2_ZIMMER)
    assert score(listing, make_profile()).rejected


def test_far_over_budget_is_rejected():
    assert score(make_listing(warmmiete=700), make_profile()).rejected


def test_too_far_away_is_rejected():
    frankfurt = make_listing(lat=50.1109, lon=8.6821)
    assert score(frankfurt, make_profile()).rejected


def test_cheaper_beats_pricier():
    cheap = score(make_listing(warmmiete=350), make_profile()).total
    pricey = score(make_listing(warmmiete=500), make_profile()).total
    assert cheap > pricey


def test_unknown_values_give_middle_score():
    result = score(make_listing(), make_profile())
    assert result.total == 50


def test_wrong_move_in_date_costs_points():
    early = score(make_listing(available_from=date(2026, 11, 1)), make_profile()).total
    fine = score(make_listing(available_from=date(2027, 1, 1)), make_profile()).total
    assert fine > early


# --- Profiles ----------------------------------------------------------------

def test_repo_profiles_load():
    profiles = load_profiles()
    assert set(profiles) == {"newfreshhorizonx", "souissinebilai", "team"}
    assert HousingType.WOHNUNG_2_ZIMMER in profiles["team"].housing_types
    assert "Schach" in profiles["newfreshhorizonx"].hobbies
