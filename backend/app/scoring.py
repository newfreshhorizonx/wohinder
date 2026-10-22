"""Rule-based compatibility score (0–100) between a listing and a profile.

This is the fast, free first pass. In milestone 3 an AI check adds points for
vibe and subtracts for red flags (Befristung, no Anmeldung, "nur Frauen", ...).
"""

from __future__ import annotations

import math

from .models import Listing, Profile, ScoreBreakdown

# Max points per category (sum = 100)
PRICE_POINTS = 40
DISTANCE_POINTS = 25
DATE_POINTS = 20
SIZE_POINTS = 15

# Unknown values get half the points: not a dealbreaker, but less attractive.
UNKNOWN_SHARE = 0.5

# Tolerance before a listing is rejected outright
BUDGET_TOLERANCE = 1.10   # up to 10 % over budget still shown, with low score
RADIUS_TOLERANCE = 1.5


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two coordinates (haversine formula)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def score(listing: Listing, profile: Profile) -> ScoreBreakdown:
    reasons: list[str] = []

    # --- Hard filters -------------------------------------------------------
    if listing.housing_type and listing.housing_type not in profile.housing_types:
        return ScoreBreakdown(total=0, rejected=True,
                              reasons=[f"Typ {listing.housing_type.value} nicht gesucht"])

    if listing.warmmiete and listing.warmmiete > profile.max_warmmiete * BUDGET_TOLERANCE:
        return ScoreBreakdown(total=0, rejected=True,
                              reasons=[f"{listing.warmmiete} € deutlich über Budget"])

    dist = None
    if listing.lat is not None and listing.lon is not None:
        dist = distance_km(profile.center.lat, profile.center.lon, listing.lat, listing.lon)
        if dist > profile.radius_km * RADIUS_TOLERANCE:
            return ScoreBreakdown(total=0, rejected=True,
                                  reasons=[f"{dist:.1f} km entfernt, zu weit"])

    total = 0.0

    # --- Price: cheaper is better, full points at ≤ 70 % of budget ----------
    if listing.warmmiete is None:
        total += PRICE_POINTS * UNKNOWN_SHARE
        reasons.append("Preis unbekannt")
    else:
        ratio = listing.warmmiete / profile.max_warmmiete
        share = 1.0 if ratio <= 0.7 else max(0.0, (1.1 - ratio) / 0.4)
        total += PRICE_POINTS * share
        reasons.append(f"{listing.warmmiete} € warm ({ratio:.0%} vom Budget)")

    # --- Distance: full points within half the radius ----------------------
    if dist is None:
        total += DISTANCE_POINTS * UNKNOWN_SHARE
        reasons.append("Lage unbekannt")
    else:
        half = profile.radius_km / 2
        share = 1.0 if dist <= half else max(0.0, 1 - (dist - half) / (profile.radius_km * RADIUS_TOLERANCE - half))
        total += DISTANCE_POINTS * share
        reasons.append(f"{dist:.1f} km bis {profile.center.name}")

    # --- Move-in date --------------------------------------------------------
    if listing.available_from is None or profile.move_in_from is None:
        total += DATE_POINTS * UNKNOWN_SHARE
    else:
        too_early = listing.available_from < profile.move_in_from
        too_late = profile.move_in_until is not None and listing.available_from > profile.move_in_until
        if too_early or too_late:
            reasons.append(f"frei ab {listing.available_from:%d.%m.%Y} passt nicht")
        else:
            total += DATE_POINTS
            reasons.append(f"frei ab {listing.available_from:%d.%m.%Y}")

    # --- Size ----------------------------------------------------------------
    if listing.size_m2 is None or profile.min_size_m2 is None:
        total += SIZE_POINTS * UNKNOWN_SHARE
    else:
        share = min(1.0, listing.size_m2 / profile.min_size_m2)
        total += SIZE_POINTS * share
        reasons.append(f"{listing.size_m2:g} m²")

    return ScoreBreakdown(total=round(total), reasons=reasons)
