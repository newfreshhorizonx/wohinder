"""Pick the right Anrede for an Anfrage based on the listing's contact."""

from __future__ import annotations

import re

from .models import HousingType, Listing

_WG_TYPES = {HousingType.WG_2, HousingType.WG_3, HousingType.WG_4}

# "Frau Müller", "Fr. Müller", "Herr Schmidt", "Hr. Schmidt"
_FORMAL = re.compile(r"\b(Frau|Fr\.|Herr|Hr\.)\s+([A-ZÄÖÜ][\w\-äöüß]+)")
# A single first name like "Lena" or "Jan-Luca"
_FIRST_NAME = re.compile(r"^[A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)?$")


def greeting_for(listing: Listing) -> str:
    """Return the opening line of the Anfrage, e.g. 'Sehr geehrte Frau Müller,'."""
    name = (listing.contact_name or "").strip()

    match = _FORMAL.search(name)
    if match:
        title, surname = match.groups()
        if title in ("Frau", "Fr."):
            return f"Sehr geehrte Frau {surname},"
        return f"Sehr geehrter Herr {surname},"

    if "wg" in name.lower():
        return "Hallo liebe WG,"

    # A first name wins over the listing type: "Lena" in a 2er-WG is still Lena.
    if _FIRST_NAME.match(name):
        return f"Hallo {name},"

    if listing.housing_type in _WG_TYPES:
        return "Hallo liebe WG,"

    # Unknown contact or a company ("Immobilien GmbH"): stay neutral and polite.
    if name:
        return "Sehr geehrte Damen und Herren,"
    return "Hallo,"
