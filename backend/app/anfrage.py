"""Build the Anfrage text for a listing (simple template).

Milestone 3 replaces this with an AI-written, personalized message. Until then
the template already gets the important parts right: the greeting, the matching
form of address (Sie / du / ihr), the profile text and the contact details.
"""

from __future__ import annotations

from .greeting import greeting_for
from .models import Listing, Profile

MISSING_EMAIL = "[E-Mail fehlt: in .env eintragen]"


def _address_form(greeting: str) -> str:
    """'sie' for formal greetings, 'ihr' for a WG, 'du' for a first name."""
    if greeting == "Hallo liebe WG,":
        return "ihr"
    if greeting.startswith("Hallo ") and greeting != "Hallo,":
        return "du"
    return "sie"


# Phrases per form of address: (your listing, you can reach me)
_PHRASES = {
    "sie": ("Ihre", "Sie erreichen"),
    "du": ("deine", "Du erreichst"),
    "ihr": ("eure", "Ihr erreicht"),
}


def anfrage_for(listing: Listing, profile: Profile) -> str:
    """Return the full Anfrage text for one listing, ready to send."""
    greeting = greeting_for(listing)
    your, reach = _PHRASES[_address_form(greeting)]
    we = len(profile.members) > 1  # team profile writes as "wir"

    seen = (f"wir haben {your} Anzeige „{listing.title}“ gesehen und interessieren uns sehr dafür."
            if we else
            f"ich habe {your} Anzeige „{listing.title}“ gesehen und interessiere mich sehr dafür.")

    contact = profile.contact_email or MISSING_EMAIL
    if profile.contact_phone:
        contact += f" oder telefonisch unter {profile.contact_phone}"
    me = "uns" if we else "mich"
    reach_line = f"{reach} {me} per E-Mail unter {contact}."

    closing = ("Wir würden uns sehr über eine Rückmeldung und einen Besichtigungstermin freuen."
               if we else
               "Ich würde mich sehr über eine Rückmeldung und einen Besichtigungstermin freuen.")

    # " ".join(text.split()) turns the multi-line YAML text into one clean paragraph
    about_me = " ".join(profile.about_me.split())

    return "\n\n".join([
        greeting,
        seen,
        about_me,
        f"{closing} {reach_line}",
        f"Viele Grüße\n{profile.display_name}",
    ])
