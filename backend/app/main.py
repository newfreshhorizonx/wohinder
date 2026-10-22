"""Wohinder API. Run with: uvicorn app.main:app --reload"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .greeting import greeting_for
from .models import Listing, Profile, ScoreBreakdown
from .profiles import load_profiles
from .scoring import score

app = FastAPI(title="Wohinder", description="Swipe your way to your next Wohnung.")
profiles = load_profiles()


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
