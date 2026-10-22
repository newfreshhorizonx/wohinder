# Wohinder 🏠

**Wohinder – dein Wohnungsfinder.** Swipe your way to your next Wohnung.

Automated apartment search for students in Darmstadt. Wohinder collects listings from
WG-Gesucht, Kleinanzeigen and ImmoScout24 alert emails, scores how well each one fits
your profile, and sends a personalized Anfrage with a single swipe.

## How it works

1. **Collect:** saved searches on the listing sites send alert emails to a dedicated inbox.
   Wohinder reads them, extracts the listings and removes duplicates.
2. **Score:** each listing gets a compatibility score (0–100) for every profile:
   price, room type, size, move-in date, plus an AI check for red flags and vibe.
3. **Swipe:** matches show up as cards on your phone. Right = send Anfrage, left = skip.
4. **Write:** the Anfrage is personalized for the listing, with the correct greeting
   (Frau / Herr / liebe WG) and your profile and contact info.
5. **Track:** replies are shown per listing (sent → answered → Besichtigung).

## Profiles

| Profile | Who | Searches for |
|---|---|---|
| `newfreshhorizonx` | Mayyas | Einzelzimmer, WGs |
| `souissinebilai` | souissinebilAI | Einzelzimmer, WGs |
| `team` | both | 2er-WG together, 2-Zimmer-Wohnung |

Profiles live in [`profiles/`](profiles/) as YAML files. Contact details (email, phone)
are **not** stored in git. They come from the `.env` file (see `.env.example`).

## Tech stack

- **Backend:** Python 3.11+ · FastAPI · SQLite
- **AI:** Claude API (scoring details + message writing)
- **App:** Progressive Web App (installable on iPhone, no App Store needed)
- **Hosting:** small VPS (e.g. Hetzner, ~4 €/month)

## Getting started (local)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env      # then fill in your values
pytest                          # run the tests
uvicorn app.main:app --reload   # start the API on http://localhost:8000
```

Open http://localhost:8000/docs to try the API in the browser.

## Project structure

```
wohinder/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app & routes
│   │   ├── models.py      # data models (Profile, Listing, ...)
│   │   ├── profiles.py    # loads profiles from YAML + .env
│   │   ├── scoring.py     # compatibility score
│   │   └── greeting.py    # Anrede detection (Frau / Herr / WG)
│   └── tests/
├── profiles/              # one YAML file per profile
└── PLAN.md                # roadmap & decisions
```

## Team

- [@newfreshhorizonx](https://github.com/newfreshhorizonx)
- [@souissinebilAI](https://github.com/souissinebilAI)

Both studying Informatik at h_da.
