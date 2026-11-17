"""Wohinder API. Run with: uvicorn app.main:app --reload"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .anfrage import anfrage_for
from .db import DEFAULT_DB, ListingStore
from .fake_listings import FAKE_LISTINGS
from .greeting import greeting_for
from .importer import run_import
from .mail import Inbox
from .models import Listing, Profile, ScoreBreakdown
from .profiles import load_profiles
from .scoring import score
from .swipes import Swipe, SwipeStore

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="Wohinder", description="Swipe your way to your next Wohnung.")
profiles = load_profiles()

# The local database filled by `python -m app.importer`. Tests point this at a
# temp file. In the cloud, DATABASE_URL (Postgres) is used instead.
LISTING_DB: Path | str = DEFAULT_DB


def _db_target() -> Path | str:
    return os.environ.get("DATABASE_URL") or LISTING_DB


def get_swipes() -> Iterator[SwipeStore]:
    """One database connection per request, closed afterwards.

    FastAPI runs this for every route that asks for `Depends(get_swipes)`:
    the code before `yield` runs before the route, the `finally` part after it.
    """
    store = SwipeStore(_db_target())
    try:
        yield store
    finally:
        store.close()


def _imported_listings() -> list[Listing]:
    store = ListingStore(_db_target())
    try:
        return store.all()
    finally:
        store.close()


def _listings() -> dict[str, Listing]:
    """Listings for the swipe app: the imported ones, or the fake ones while there are none.

    Read on every request, so newly imported listings show up without a restart.
    """
    # `a or b` returns b when a is empty, like `a.isEmpty() ? b : a` in Java
    return {listing.id: listing for listing in _imported_listings() or FAKE_LISTINGS}


def _get_profile(profile_id: str) -> Profile:
    if profile_id not in profiles:
        raise HTTPException(404, f"Unknown profile '{profile_id}'")
    return profiles[profile_id]


# --- Login: one shared password for both of you (APP_PASSWORD) ---------------
# Without APP_PASSWORD (on the laptop, in tests) the app stays open.

LOGIN_COOKIE = "wohinder_login"
LOGIN_DAYS = 365
OPEN_PATHS = {"/login", "/api/import"}   # /api/import checks its own secret

LOGIN_PAGE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wohinder – Login</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #f4f1ec; display: grid;
         place-items: center; min-height: 100vh; margin: 0; padding: 16px; }}
  form {{ background: #fff; padding: 24px; border-radius: 16px; width: 100%; max-width: 320px;
         box-shadow: 0 4px 20px rgba(0,0,0,.08); }}
  h1 {{ margin: 0 0 16px; font-size: 24px; }}
  input, button {{ width: 100%; box-sizing: border-box; font-size: 16px; padding: 12px;
                  border-radius: 10px; margin-top: 8px; }}
  input {{ border: 1px solid #ccc; }}
  button {{ border: 0; background: #e8604c; color: #fff; font-weight: 600; }}
  p {{ color: #c0392b; margin: 8px 0 0; }}
</style></head>
<body><form method="post" action="/login">
  <h1>Wohinder</h1>
  <input type="password" name="password" placeholder="Passwort" autofocus required>
  <button>Einloggen</button>{error}
</form></body></html>"""


def _login_token() -> str | None:
    """What the login cookie must contain; None when no password is set.

    It's a hash of the password, so the cookie never holds the password itself,
    and changing APP_PASSWORD logs everyone out.
    """
    password = os.environ.get("APP_PASSWORD")
    if not password:
        return None
    return hashlib.sha256(f"wohinder-login:{password}".encode()).hexdigest()


def _same(a: str, b: str) -> bool:
    # compare_digest takes the same time whether the strings match early or late,
    # so an attacker can't guess the secret character by character.
    return hmac.compare_digest(a.encode(), b.encode())


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Runs before every request, like a servlet filter in Java."""
    token = _login_token()
    if token is None or request.url.path in OPEN_PATHS \
            or _same(request.cookies.get(LOGIN_COOKIE, ""), token):
        return await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/app"):
        return RedirectResponse("/login")
    return JSONResponse({"detail": "Login required"}, status_code=401)


@app.get("/login", include_in_schema=False)
def login_page() -> HTMLResponse:
    return HTMLResponse(LOGIN_PAGE.format(error=""))


@app.post("/login", include_in_schema=False)
async def login(request: Request):
    # The form arrives as "password=..."; parse_qs turns it into {"password": ["..."]}
    form = parse_qs((await request.body()).decode())
    password = form.get("password", [""])[0]
    expected = os.environ.get("APP_PASSWORD", "")
    if not expected or not _same(password, expected):
        await asyncio.sleep(1)   # slows down anyone trying many passwords
        return HTMLResponse(LOGIN_PAGE.format(error="<p>Falsches Passwort</p>"), status_code=401)

    response = RedirectResponse("/app/", status_code=303)
    https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    response.set_cookie(LOGIN_COOKIE, _login_token(), max_age=LOGIN_DAYS * 24 * 3600,
                        httponly=True, secure=https, samesite="lax")
    return response


# --- Import, called every 30 minutes by .github/workflows/import.yml ----------

@app.post("/api/import")
def import_emails(authorization: str = Header("")) -> dict:
    """Read new alert emails into the database. Needs `Authorization: Bearer <IMPORT_SECRET>`."""
    secret = os.environ.get("IMPORT_SECRET")
    if not secret or not _same(authorization, f"Bearer {secret}"):
        raise HTTPException(401, "Wrong or missing import secret")
    store = ListingStore(_db_target())
    try:
        with Inbox() as inbox:
            result = run_import(inbox, store)
    finally:
        store.close()
    return asdict(result)   # dataclass -> dict, which FastAPI sends as JSON


@app.get("/health")
def health() -> dict:
    source = "database" if _imported_listings() else "fake"
    return {"status": "ok", "profiles": list(profiles), "listings": source}


@app.get("/profiles")
def list_profiles() -> list[Profile]:
    # Contact details are hidden from the list view
    return [p.model_copy(update={"contact_email": None, "contact_phone": None})
            for p in profiles.values()]


@app.get("/profiles/{profile_id}")
def get_profile(profile_id: str) -> Profile:
    return _get_profile(profile_id)


@app.get("/listings")
def list_listings() -> list[Listing]:
    """Everything imported from alert emails so far, newest first."""
    return _imported_listings()


@app.post("/profiles/{profile_id}/score")
def score_listing(profile_id: str, listing: Listing) -> dict:
    """Try the scorer by hand: POST a listing, get score + greeting back."""
    profile = _get_profile(profile_id)
    result: ScoreBreakdown = score(listing, profile)
    return {"score": result, "greeting": greeting_for(listing)}


# --- Swipe app (M4) ----------------------------------------------------------

@app.get("/profiles/{profile_id}/feed")
def feed(profile_id: str, swipes: SwipeStore = Depends(get_swipes)) -> list[dict]:
    """Listings not swiped yet, best match first. Rejected listings are left out."""
    profile = _get_profile(profile_id)
    done = swipes.swiped_ids(profile_id)
    cards = []
    for listing in _listings().values():
        if listing.id in done:
            continue
        result = score(listing, profile)
        if not result.rejected:
            cards.append({"listing": listing, "score": result})
    # Sort by score, highest first. key= is like a Comparator in Java, as a lambda.
    cards.sort(key=lambda card: card["score"].total, reverse=True)
    return cards


@app.post("/profiles/{profile_id}/swipes")
def record_swipe(profile_id: str, swipe: Swipe,
                 swipes: SwipeStore = Depends(get_swipes)) -> dict:
    """Save a swipe. A right swipe returns the Anfrage preview (nothing is sent yet)."""
    profile = _get_profile(profile_id)
    listing = _listings().get(swipe.listing_id)
    if listing is None:
        raise HTTPException(404, f"Unknown listing '{swipe.listing_id}'")
    swipes.record(profile_id, swipe)
    anfrage = anfrage_for(listing, profile) if swipe.direction == "right" else None
    return {"listing_id": listing.id, "direction": swipe.direction, "anfrage": anfrage}


@app.get("/profiles/{profile_id}/swipes")
def list_swipes(profile_id: str, swipes: SwipeStore = Depends(get_swipes)) -> list[Swipe]:
    _get_profile(profile_id)
    return swipes.all(profile_id)


@app.delete("/profiles/{profile_id}/swipes/{listing_id}")
def undo_swipe(profile_id: str, listing_id: str,
               swipes: SwipeStore = Depends(get_swipes)) -> dict:
    """Undo one swipe: the listing shows up in the feed again."""
    _get_profile(profile_id)
    if not swipes.remove(profile_id, listing_id):
        raise HTTPException(404, f"No swipe for listing '{listing_id}'")
    return {"status": "undone", "listing_id": listing_id}


@app.get("/profiles/{profile_id}/saved")
def saved(profile_id: str, swipes: SwipeStore = Depends(get_swipes)) -> list[dict]:
    """Listings swiped right ("Gemerkt"), newest first, each with its Anfrage."""
    profile = _get_profile(profile_id)
    listings = _listings()
    items = []
    for listing_id in swipes.right_ids(profile_id):
        listing = listings.get(listing_id)
        if listing is None:  # listing vanished from the source
            continue
        items.append({"listing": listing, "score": score(listing, profile),
                      "anfrage": anfrage_for(listing, profile)})
    return items


@app.delete("/profiles/{profile_id}/swipes")
def reset_swipes(profile_id: str, swipes: SwipeStore = Depends(get_swipes)) -> dict:
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
