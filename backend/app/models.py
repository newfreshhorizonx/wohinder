"""Data models shared across the backend."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class HousingType(str, Enum):
    """What kind of place a listing is, or a profile is looking for."""

    EINZELZIMMER = "einzelzimmer"   # own room / 1-Zimmer-Wohnung
    WG_2 = "wg_2"                   # room in a 2er-WG
    WG_3 = "wg_3"
    WG_4 = "wg_4"                   # 4 or more people
    WOHNUNG_2_ZIMMER = "wohnung_2_zimmer"  # whole flat for two (team profile)


class Location(BaseModel):
    name: str
    lat: float
    lon: float


class Profile(BaseModel):
    """One person (or the team) searching for a place."""

    id: str
    display_name: str
    members: list[str] = Field(description="GitHub usernames of the people in this profile")

    # Search criteria
    housing_types: list[HousingType]
    max_warmmiete: int = Field(description="Max total rent incl. Nebenkosten, in €")
    min_size_m2: int | None = None
    radius_km: float
    center: Location
    move_in_from: date | None = None
    move_in_until: date | None = None

    # Used in Anfragen
    about_me: str
    study: str
    hobbies: list[str] = []
    personality: str = ""

    # Filled from .env, never stored in git
    contact_email: str | None = None
    contact_phone: str | None = None


class Listing(BaseModel):
    """A listing extracted from an alert email."""

    id: str
    source: str                      # "wg-gesucht" | "kleinanzeigen" | "immoscout"
    url: str
    title: str
    housing_type: HousingType | None = None
    warmmiete: int | None = None     # € per month, if known
    size_m2: float | None = None
    lat: float | None = None
    lon: float | None = None
    available_from: date | None = None
    contact_name: str | None = None  # e.g. "Frau Müller", "Max", "WG Kranichstein"
    contact_email: str | None = None
    description: str = ""


class ScoreBreakdown(BaseModel):
    total: int = Field(ge=0, le=100)
    rejected: bool = False           # hard filter failed (e.g. wrong type, far over budget)
    reasons: list[str] = []
