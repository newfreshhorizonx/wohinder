# CLAUDE.md – context for Claude Code

## Project
Wohinder ("wohin" + Wohnung + Tinder): apartment search app for two Informatik
students at h_da (Darmstadt): Mayyas (@newfreshhorizonx) and @souissinebilAI.
Read `PLAN.md` for decisions and milestones before starting work.

## The people
- Mayyas knows C++ and Java, some HTML/CSS, and is **learning Python** with this
  project. Explain Python idioms briefly when they differ from Java/C++.
- Both use iPhones → the app is a PWA, not a native iOS app.
- Development machine: Windows (PowerShell).

## Architecture
- `backend/` Python 3.11+, FastAPI, SQLite (planned), pydantic models.
- `profiles/*.yaml` one per profile (`newfreshhorizonx`, `souissinebilai`, `team`).
- Listings come from the sites' **alert emails** (IMAP), not from scraping.

## Hard rules
- **Never commit secrets or contact data.** Gmail app password, API keys, phone
  numbers and personal emails live only in `.env` (gitignored).
- Don't scrape WG-Gesucht / Kleinanzeigen / ImmoScout directly; use alert emails.
- Sending through platform messaging is an **open decision** (ToS / ban risk):
  don't build it until the user decides (see PLAN.md).
- Anfragen are German. Code, comments and commits are English.

## Commands (run inside `backend/`)
```powershell
.venv\Scripts\activate
pytest                          # tests
uvicorn app.main:app --reload   # API on http://localhost:8000/docs
```
