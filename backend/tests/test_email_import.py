"""Tests for the email import: parsing, dedup and the importer. No network needed.

The emails here are invented. Replace them with anonymised copies of real alert
emails once those arrive, so the parser is tested against the real layout.
"""

from datetime import date
from email.message import EmailMessage

from app.db import ListingStore
from app.importer import run_import
from app.mail import AlertEmail, parse_message
from app.models import HousingType
from app.parsers import parse_alert

WG_HTML = """
<html><body>
  <h1>Neue Angebote für Ihren Suchauftrag</h1>
  <table>
    <tr><td>
      <a href="https://www.wg-gesucht.de/wg-zimmer-in-Darmstadt-Bessungen.1111111.html?utm_source=mail">
        <img src="photo.jpg"></a>
      <a href="https://www.wg-gesucht.de/wg-zimmer-in-Darmstadt-Bessungen.1111111.html?utm_source=mail">
        Helles Zimmer in netter 3er WG</a>
      <p>16 m² | 420 € | frei ab 01.12.2026</p>
    </td></tr>
    <tr><td>
      <a href="https://www.wg-gesucht.de/1-zimmer-wohnungen-in-Darmstadt-Martinsviertel.2222222.html">
        Kleine Wohnung nahe h_da</a>
      <p>28 m² | 1.050 € | ab 15.01.27</p>
    </td></tr>
  </table>
  <a href="https://www.wg-gesucht.de/mein-wg-gesucht.html">Suchauftrag verwalten</a>
</body></html>
"""

KA_TEXT = """Neue Anzeigen für "Wohnung Darmstadt"

Schöne 2-Zimmer-Wohnung, 52 m², 780 €
https://www.kleinanzeigen.de/s-anzeige/schoene-2-zimmer-wohnung/3012345678-203-4991

Zimmer in 4er WG frei
https://www.kleinanzeigen.de/s-anzeige/zimmer-in-4er-wg/3087654321-199-4991?utm=x
"""


def make_alert(uid=1, source="wg-gesucht", html="", text="") -> AlertEmail:
    return AlertEmail(uid=uid, source=source, subject="Neue Angebote", received=None,
                      html=html, text=text)


class FakeInbox:
    """Stands in for app.mail.Inbox: same fetch_alerts() method, no network."""

    def __init__(self, alerts):
        self.alerts = alerts

    def fetch_alerts(self, after_uid=0):
        return (a for a in self.alerts if a.uid > after_uid)


# --- Parsing -----------------------------------------------------------------

def test_wg_gesucht_html():
    listings = parse_alert(make_alert(html=WG_HTML))
    assert [l.id for l in listings] == ["wg-gesucht:1111111", "wg-gesucht:2222222"]

    zimmer, wohnung = listings
    assert zimmer.title == "Helles Zimmer in netter 3er WG"
    assert zimmer.url == "https://www.wg-gesucht.de/wg-zimmer-in-Darmstadt-Bessungen.1111111.html"
    assert zimmer.housing_type == HousingType.WG_3
    assert (zimmer.warmmiete, zimmer.size_m2) == (420, 16)
    assert zimmer.available_from == date(2026, 12, 1)

    assert wohnung.housing_type == HousingType.EINZELZIMMER
    assert wohnung.warmmiete == 1050
    assert wohnung.available_from == date(2027, 1, 15)


def test_kleinanzeigen_plain_text():
    listings = parse_alert(make_alert(source="kleinanzeigen", text=KA_TEXT))
    assert [l.id for l in listings] == ["kleinanzeigen:3012345678", "kleinanzeigen:3087654321"]
    assert listings[0].housing_type == HousingType.WOHNUNG_2_ZIMMER
    assert (listings[0].warmmiete, listings[0].size_m2) == (780, 52)
    assert listings[1].housing_type == HousingType.WG_4
    assert "?" not in listings[1].url   # tracking parameters removed


def test_email_without_listings():
    assert parse_alert(make_alert(html="<p>Bitte bestätigen Sie Ihre E-Mail-Adresse</p>")) == []


def test_parse_raw_message():
    msg = EmailMessage()
    msg["Subject"] = "=?utf-8?q?Neue_Angebote_f=C3=BCr_Darmstadt?="
    msg["Date"] = "Thu, 22 Oct 2026 18:00:00 +0200"
    msg.set_content("Plain version")
    msg.add_alternative("<p>HTML version</p>", subtype="html")

    alert = parse_message(7, "wg-gesucht", msg.as_bytes())
    assert alert.subject == "Neue Angebote für Darmstadt"
    assert alert.received.day == 22
    assert "Plain version" in alert.text
    assert "HTML version" in alert.html


# --- Database ----------------------------------------------------------------

def test_store_skips_duplicates():
    store = ListingStore(":memory:")
    listing = parse_alert(make_alert(html=WG_HTML))[0]
    assert store.add(listing) is True
    assert store.add(listing) is False
    assert store.count() == 1
    assert store.all()[0] == listing


# --- Importer ----------------------------------------------------------------

def test_import_dedups_across_emails_and_runs():
    store = ListingStore(":memory:")
    inbox = FakeInbox([
        make_alert(uid=1, html=WG_HTML),
        make_alert(uid=2, html=WG_HTML),   # same listings again in a later email
        make_alert(uid=3, source="kleinanzeigen", text=KA_TEXT),
    ])

    result = run_import(inbox, store)
    assert (result.emails, result.listings, result.new) == (3, 6, 4)
    assert result.empty == []
    assert store.get_state("last_email_uid") == "3"

    # Second run: no new emails, nothing happens
    again = run_import(inbox, store)
    assert (again.emails, again.new) == (0, 0)
    assert store.count() == 4


def test_import_reports_emails_without_listings():
    store = ListingStore(":memory:")
    inbox = FakeInbox([make_alert(uid=1, html="<p>Aktiviere dein Konto</p>")])
    assert run_import(inbox, store).empty == ["wg-gesucht: Neue Angebote"]
