"""Wohinder API. Run with: uvicorn app.main:app --reload"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .anfrage import anfrage_for
from .fake_listings import FAKE_LISTINGS
from .greeting import greeting_for
from .models import Listing, Profile, ScoreBreakdown
from .profiles import load_profiles
from .scoring import score
from .swipes import Swipe, SwipeStore

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="Wohinder", description="Swipe your way to your next Wohnung.")
profiles = load_profiles()
swipes = SwipeStore()

# Listing source. TODO(M2): read from the database instead of the fake listings.
listings: dict[str, Listing] = {listing.id: listing for listing in FAKE_LISTINGS}


def _get_profile(profile_id: str) -> Profile:
    if profile_id not in profiles:
        raise HTTPException(404, f"Unknown profile '{profile_id}'")
    return profiles[profile_id]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "profiles": list(profiles)}


@app.get("/profiles")
def list_profiles() -> list[Profile]:
    # Contact details are hidden from the list view
    return [p.model_copy(update={"contact_email": None, "contact_phone": None})
            for p in profiles.values()]


@app.get("/profiles/{profile_id}")
def get_profile(profile_id: str) -> Profile:
    return _get_profile(profile_id)


@app.post("/profiles/{profile_id}/score")
def score_listing(profile_id: str, listing: Listing) -> dict:
    """Try the scorer by hand: POST a listing, get score + greeting back."""
    profile = _get_profile(profile_id)
    result: ScoreBreakdown = score(listing, profile)
    return {"score": result, "greeting": greeting_for(listing)}


# --- Swipe app (M4) ----------------------------------------------------------

@app.get("/profiles/{profile_id}/feed")
def feed(profile_id: str) -> list[dict]:
    """Listings not swiped yet, best match first. Rejected listings are left out."""
    profile = _get_profile(profile_id)
    done = swipes.swiped_ids(profile_id)
    cards = []
    for listing in listings.values():
        if listing.id in done:
            continue
        result = score(listing, profile)
        if not result.rejected:
            cards.append({"listing": listing, "score": result})
    # Sort by score, highest first. key= is like a Comparator in Java, as a lambda.
    cards.sort(key=lambda card: card["score"].total, reverse=True)
    return cards


@app.post("/profiles/{profile_id}/swipes")
def record_swipe(profile_id: str, swipe: Swipe) -> dict:
    """Save a swipe. A right swipe returns the Anfrage preview (nothing is sent yet)."""
    profile = _get_profile(profile_id)
    listing = listings.get(swipe.listing_id)
    if listing is None:
        raise HTTPException(404, f"Unknown listing '{swipe.listing_id}'")
    swipes.record(profile_id, swipe)
    anfrage = anfrage_for(listing, profile) if swipe.direction == "right" else None
    return {"listing_id": listing.id, "direction": swipe.direction, "anfrage": anfrage}


@app.get("/profiles/{profile_id}/swipes")
def list_swipes(profile_id: str) -> list[Swipe]:
    _get_profile(profile_id)
    return swipes.all(profile_id)


@app.delete("/profiles/{profile_id}/swipes/{listing_id}")
def undo_swipe(profile_id: str, listing_id: str) -> dict:
    """Undo one swipe: the listing shows up in the feed again."""
    _get_profile(profile_id)
    if not swipes.remove(profile_id, listing_id):
        raise HTTPException(404, f"No swipe for listing '{listing_id}'")
    return {"status": "undone", "listing_id": listing_id}


@app.get("/profiles/{profile_id}/saved")
def saved(profile_id: str) -> list[dict]:
    """Listings swiped right ("Gemerkt"), newest first, each with its Anfrage."""
    profile = _get_profile(profile_id)
    items = []
    for listing_id in swipes.right_ids(profile_id):
        listing = listings.get(listing_id)
        if listing is None:  # listing vanished from the source
            continue
        items.append({"listing": listing, "score": score(listing, profile),
                      "anfrage": anfrage_for(listing, profile)})
    return items


@app.delete("/profiles/{profile_id}/swipes")
def reset_swipes(profile_id: str) -> dict:
    """Forget all swipes of a profile, so every listing shows up again (for testing)."""
    _get_profile(profile_id)
    swipes.reset(profile_id)
    return {"status": "reset"}


# --- Serve the PWA under /app/ -------------------------------------------------

@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/app/")


if FRONTEND_DIR.exists():
    # html=True serves index.html for /app/
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="app")
