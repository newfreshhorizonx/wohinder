# Wohinder – Plan & Decisions

## Goal

Two Informatik students at h_da want to stop spending time every day searching
WG-Gesucht, Kleinanzeigen and ImmoScout and writing Anfragen by hand.
Open the app → swipe through good matches → done.

## Decisions so far

| Topic | Decision | Why |
|---|---|---|
| Name | **Wohinder** (wohin + Wohnung + Tinder) | |
| Phones | Both iPhone → **PWA** (web app on home screen) | Native iOS needs a Mac + 99 €/year, or reinstalls every 7 days |
| Backend | **Python + FastAPI** | Easy to learn coming from Java/C++, great libraries |
| Finding listings | **Read the sites' own alert emails** from a dedicated Gmail inbox | No scraping → no bans, stable |
| Sites | **WG-Gesucht + Kleinanzeigen**; ImmoScout skipped for now | ImmoScout needs a paid subscription to send Anfragen |
| Interaction | **Swipe**: right = send Anfrage, left = skip | Minimum effort, that's the whole point |
| Greeting | Detected from the listing (Frau / Herr / liebe WG / neutral) | |
| Profiles | 3 profiles: each person + `team` | Search separately *and* together |
| Search types | Einzelzimmer, 2er/3er/4er-WG, whole Wohnung | |
| Costs | Few €/month (server + Claude API), shut down after the search | |
| Secrets | Never in git: `.env` only (Gmail app password, API key, phone) | |

## Open decision: sending via WG-Gesucht / Kleinanzeigen messaging

Sending to an email address is safe and fully automatic. Sending through the
platforms' own messaging means the app acts as your logged-in account, which their
terms forbid, so the account could get banned. If we build it: only on swipe, never
in bulk, human pace, daily limits. **Decide after milestone 4.**

## Milestones

- [x] **M0** Repo, README, plan
- [x] **M1** Backend skeleton, profiles, rule-based score, greeting detection
- [ ] **M2** ← *next* Read alert emails (IMAP) → parse listings → SQLite, deduplicate
      → *switch to Claude Code on the laptop here (credentials stay local)*
- [ ] **M3** AI scoring (red flags, vibe) + AI-written Anfrage
- [ ] **M4** Swipe PWA on both iPhones
- [ ] **M5** Sending: email first; platform messaging if decided
- [ ] **M6** Reply tracking + push notifications for new top matches
- [ ] **M7** Deploy to a small server

## Team workflow

- `main` = working version only. Each person works on a **branch** and merges via **pull request**.
- **Mayyas:** M2 email import (branch `email-import`). His laptop holds the inbox credentials.
- **souissinebilAI:** M4 swipe PWA with fake listings (own branch), plugged into real data later.

## Still to collect

- [ ] Profile details for both (budget Warmmiete, Umkreis, move-in date, size)
- [ ] souissinebilAI's "about me" text
- [ ] Saved searches on the three sites → alerts to the app inbox
