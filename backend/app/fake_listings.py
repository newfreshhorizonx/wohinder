"""Fake listings for building the swipe app before the email import (M2) exists.

They look like real Darmstadt listings (prices, Stadtteile, contacts) so the
scoring, greetings and Anfrage preview can be tested end to end. Some are made
to hit edge cases on purpose: far over budget, unknown price/location, wrong
move-in date, a whole flat that only fits the team profile.

Once M2 is merged, the API reads listings from the database instead.
"""

from __future__ import annotations

from datetime import date

from .models import HousingType, Listing

_T = HousingType


def _fake(n: int, **fields) -> Listing:
    """Build a listing with a fake id and URL (example.org never is a real listing)."""
    return Listing(id=f"fake-{n}", url=f"https://example.org/fake/{n}", **fields)


FAKE_LISTINGS: list[Listing] = [
    _fake(1, source="wg-gesucht", title="Helles WG-Zimmer im Martinsviertel",
          housing_type=_T.WG_3, warmmiete=430, size_m2=16, lat=49.8795, lon=8.6625,
          available_from=date(2027, 1, 1), contact_name="WG Liebfrauenstraße",
          description="Altbau, hohe Decken, große Küche. Wir kochen ab und zu zusammen."),
    _fake(2, source="kleinanzeigen", title="Möbliertes Zimmer nahe Herrngarten",
          housing_type=_T.EINZELZIMMER, warmmiete=480, size_m2=14, lat=49.8770, lon=8.6545,
          available_from=date(2027, 2, 1), contact_name="Frau Becker",
          description="Möbliert, eigenes Bad, 5 Minuten zum Herrngarten."),
    _fake(3, source="immoscout", title="1-Zimmer-Apartment im Johannesviertel",
          housing_type=_T.EINZELZIMMER, warmmiete=590, size_m2=24, lat=49.8800, lon=8.6440,
          available_from=date(2027, 3, 1), contact_name="Musterbau Immobilien GmbH",
          description="Renoviert, Einbauküche, Balkon. Nichtraucher bevorzugt."),
    _fake(4, source="wg-gesucht", title="Zimmer in entspannter 2er-WG in Bessungen",
          housing_type=_T.WG_2, warmmiete=395, size_m2=13, lat=49.8610, lon=8.6570,
          available_from=date(2027, 1, 15), contact_name="Lena",
          description="Ich (Studentin, 23) suche eine*n ruhige*n Mitbewohner*in."),
    _fake(5, source="wg-gesucht", title="Großes Zimmer in 4er-WG Kranichstein",
          housing_type=_T.WG_4, warmmiete=360, size_m2=18, lat=49.8990, lon=8.6770,
          available_from=date(2026, 12, 1), contact_name="WG Kranichstein",
          description="Lustige 4er-WG mit Garten, Spieleabende jeden Freitag."),
    _fake(6, source="kleinanzeigen", title="Zimmer in Arheilgen, ruhige Lage",
          housing_type=_T.EINZELZIMMER, warmmiete=410, size_m2=15, lat=49.9120, lon=8.6480,
          available_from=date(2027, 4, 1), contact_name="Hr. Schneider",
          description="Zimmer im Einfamilienhaus, separater Eingang, Straßenbahn vor der Tür."),
    _fake(7, source="wg-gesucht", title="3er-WG in Eberstadt sucht Mitbewohner*in",
          housing_type=_T.WG_3, warmmiete=380, size_m2=12, lat=49.8170, lon=8.6360,
          available_from=date(2027, 2, 15), contact_name="Jonas",
          description="Zweck-WG mit netten Leuten, nah am Wald."),
    _fake(8, source="immoscout", title="Penthouse-Zimmer mit Dachterrasse",
          housing_type=_T.EINZELZIMMER, warmmiete=720, size_m2=22, lat=49.8720, lon=8.6510,
          available_from=date(2027, 1, 1), contact_name="Frau Wagner",
          description="Exklusive Lage am Luisenplatz, voll möbliert."),
    _fake(9, source="wg-gesucht", title="WG-Zimmer in Griesheim, 10 Min. mit der Straßenbahn",
          housing_type=_T.WG_3, warmmiete=340, size_m2=14, lat=49.8630, lon=8.5640,
          available_from=date(2027, 3, 1), contact_name=None,
          description="Günstig, ruhig, Linie 9 direkt in die Innenstadt."),
    _fake(10, source="kleinanzeigen", title="Kleines Zimmer in der Innenstadt",
          housing_type=_T.EINZELZIMMER, warmmiete=450, size_m2=9, lat=49.8725, lon=8.6505,
          available_from=date(2027, 1, 1), contact_name="Herr Yilmaz",
          description="Klein, aber zentral. Alles fußläufig erreichbar."),
    _fake(11, source="wg-gesucht", title="Studi-WG in Weiterstadt mit Garten",
          housing_type=_T.WG_4, warmmiete=330, size_m2=16, lat=49.9030, lon=8.5880,
          available_from=date(2027, 5, 1), contact_name="WG Weiterstadt",
          description="Vier Studis, großer Garten, Grillabende im Sommer."),
    _fake(12, source="immoscout", title="2-Zimmer-Wohnung in Bessungen – ideal für zwei",
          housing_type=_T.WOHNUNG_2_ZIMMER, warmmiete=980, size_m2=52, lat=49.8590, lon=8.6600,
          available_from=date(2027, 2, 1), contact_name="Frau Hoffmann",
          description="Zwei gleich große Zimmer, Wohnküche, Tageslichtbad."),
    _fake(13, source="wg-gesucht", title="Zimmer in 2er-WG nahe der Hochschule",
          housing_type=_T.WG_2, warmmiete=470, size_m2=15, lat=49.8680, lon=8.6400,
          available_from=date(2027, 1, 1), contact_name="Sara",
          description="3 Minuten zur h_da, Mitbewohnerin studiert Informatik."),
    _fake(14, source="kleinanzeigen", title="Günstiges WG-Zimmer in Pfungstadt",
          housing_type=_T.WG_3, warmmiete=310, size_m2=13, lat=49.8060, lon=8.6030,
          available_from=date(2027, 6, 1), contact_name="Lukas",
          description="Ruhige WG, Bus und Bahn in der Nähe."),
    _fake(15, source="wg-gesucht", title="Zimmer in Dieburg nahe Mediencampus",
          housing_type=_T.WG_3, warmmiete=350, size_m2=15, lat=49.8990, lon=8.8400,
          available_from=date(2027, 2, 1), contact_name="WG Dieburg",
          description="Perfekt für den Mediencampus, nach Darmstadt mit der Bahn."),
    _fake(16, source="kleinanzeigen", title="Zimmer frei – Details auf Anfrage",
          housing_type=_T.WG_3,
          description="Bitte meldet euch für mehr Infos."),
]
