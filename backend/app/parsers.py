"""Extract listings from alert emails.

Every alert has links to the listings, which carry the site's own listing ID
(our dedup key). Title, price, size and date are read from the text around
each link, when the email has them.

Real WG-Gesucht alerts (checked Oct 2026) only have the title, in quotes,
followed by an "Angebot ansehen" button linking to /<id>.html. No price, size
or date, so those stay unknown. Kleinanzeigen: no real alert seen yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup, Tag

from .mail import AlertEmail
from .models import HousingType, Listing


@dataclass
class SiteLinks:
    url: re.Pattern[str]   # matches a full listing URL (without query string)
    id: re.Pattern[str]    # group 1 = the site's listing ID inside that URL


SITES = {
    # Alerts: https://www.wg-gesucht.de/14270465.html
    # Website: https://www.wg-gesucht.de/wg-zimmer-in-Darmstadt-Bessungen.14270465.html
    "wg-gesucht": SiteLinks(
        url=re.compile(r"https?://(?:www\.)?wg-gesucht\.de/(?:[^\s\"'<>?#/]+?\.)?\d{5,}\.html"),
        id=re.compile(r"[/.](\d{5,})\.html$"),
    ),
    # https://www.kleinanzeigen.de/s-anzeige/schoenes-zimmer/3012345678-199-4991
    "kleinanzeigen": SiteLinks(
        url=re.compile(r"https?://(?:www\.)?kleinanzeigen\.de/s-anzeige/[^\s\"'<>?#]+"),
        id=re.compile(r"/(\d{6,})-\d+-\d+/?$"),
    ),
}

_PRICE = re.compile(r"(\d{1,2}\.\d{3}|\d{2,4})(?:,\d{2})?\s*€")
_SIZE = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*m(?:²|2)(?!\w)")
_DATE = re.compile(r"\bab\s*(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})\b")
_WG_SIZE = re.compile(r"\b(\d{1,2})\s*er[\s-]*WG\b", re.IGNORECASE)
_SPACES = re.compile(r"\s+")

# Link texts that are buttons, not titles. Then the title is the text before the link.
_BUTTON_TEXTS = {"", "angebot ansehen", "anzeige ansehen", "zur anzeige", "ansehen"}


@dataclass
class _Found:
    """One listing link found in an email, before turning it into a Listing."""
    url: str
    title: str = ""
    title_before: str = ""   # fallback: text right before a button-only link
    context: str = ""        # text around the link: price, m², date usually live here


def parse_alert(alert: AlertEmail) -> list[Listing]:
    """All listings in one alert email, each once."""
    site = SITES[alert.source]
    found = _from_html(alert.html, site) if alert.html else {}
    if not found:
        found = _from_text(alert.text, site)
    return [_to_listing(alert.source, site_id, f) for site_id, f in found.items()]


def _site_id(url: str, site: SiteLinks) -> str | None:
    match = site.id.search(url)
    return match.group(1) if match else None


def _link(href: str, site: SiteLinks) -> tuple[str, str] | None:
    """(clean listing URL, site ID) if `href` points to a listing, else None."""
    match = site.url.match(href)
    site_id = match and _site_id(match.group(0), site)
    return (match.group(0), site_id) if site_id else None


def _clean(text: str) -> str:
    return _SPACES.sub(" ", text).strip()


def _unquote(text: str) -> str:
    """'"Schönes Zimmer"' -> 'Schönes Zimmer'."""
    return text.strip().strip("\"„“”").strip()


def _text_before(link: Tag) -> str:
    """The nearest non-empty text before `link` in the document."""
    # find_all_previous walks backwards through everything before the link.
    for text in link.find_all_previous(string=True):
        if cleaned := _clean(text):
            return cleaned
    return ""


def _from_html(html: str, site: SiteLinks) -> dict[str, _Found]:
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, _Found] = {}
    for link in soup.find_all("a", href=True):
        if not (parsed := _link(link["href"], site)):
            continue
        url, site_id = parsed
        # The same listing is often linked twice (photo + title): keep the longest text.
        entry = found.setdefault(site_id, _Found(url=url))
        text = _clean(link.get_text(" "))
        if text.lower() in _BUTTON_TEXTS:
            # Photo or button: remember the text before it, in case no link has a title.
            entry.title_before = entry.title_before or _unquote(_text_before(link))
        elif len(text) > len(entry.title):
            entry.title = text
        if not entry.context:
            context = _clean(_listing_block(link, site_id, site).get_text(" "))
            entry.context = "" if context.lower() in _BUTTON_TEXTS else context
    return found


def _listing_block(link: Tag, site_id: str, site: SiteLinks) -> Tag:
    """The biggest element around `link` that still belongs to this listing only."""
    block = link
    for parent in link.parents:
        if parent.name in ("body", "html", "[document]"):
            break
        links = (_link(a["href"], site) for a in parent.find_all("a", href=True))
        if any(other[1] != site_id for other in links if other):
            break   # parent already contains another listing
        block = parent
    return block


def _from_text(text: str, site: SiteLinks) -> dict[str, _Found]:
    found: dict[str, _Found] = {}
    previous_end = 0
    for match in site.url.finditer(text):
        site_id = _site_id(match.group(0), site)
        # The lines between the previous link and this one describe the listing.
        before = text[max(previous_end, match.start() - 300):match.start()]
        previous_end = match.end()
        if site_id and site_id not in found:
            lines = [line for line in before.splitlines() if line.strip()]
            title = _unquote(lines[-1]) if lines else ""
            found[site_id] = _Found(url=match.group(0), title=title, context=_clean(before))
    return found


def _details(context: str) -> dict:
    details: dict = {}
    if m := _PRICE.search(context):
        details["warmmiete"] = int(m.group(1).replace(".", ""))
    if m := _SIZE.search(context):
        details["size_m2"] = float(m.group(1).replace(",", "."))
    if m := _DATE.search(context):
        day, month, year = (int(g) for g in m.groups())
        try:
            details["available_from"] = date(year + 2000 if year < 100 else year, month, day)
        except ValueError:
            pass   # e.g. "ab 31.02.2026" in a sloppy listing
    return details


def _housing_type(url: str, text: str) -> HousingType | None:
    if m := _WG_SIZE.search(text):
        people = int(m.group(1))
        return {2: HousingType.WG_2, 3: HousingType.WG_3}.get(people, HousingType.WG_4)
    lowered = url.lower() + " " + text.lower()
    if "1-zimmer" in lowered or "1 zimmer" in lowered:
        return HousingType.EINZELZIMMER
    if "2-zimmer" in lowered or "2 zimmer" in lowered:
        return HousingType.WOHNUNG_2_ZIMMER
    return None


def _to_listing(source: str, site_id: str, f: _Found) -> Listing:
    title = f.title or f.title_before or f"Anzeige {site_id}"
    return Listing(
        id=f"{source}:{site_id}",
        source=source,
        url=f.url,
        title=title,
        housing_type=_housing_type(f.url, f"{title} {f.context}"),
        # The context is only mined for details: in real alerts it's mostly button
        # labels and intro text, not a description of the place.
        **_details(f.context),
    )
