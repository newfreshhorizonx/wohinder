"""Import new alert emails into the database. Run: python -m app.importer"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol

from .db import ListingStore
from .mail import AlertEmail, Inbox
from .parsers import parse_alert
from .profiles import load_env

LAST_UID = "last_email_uid"


class AlertSource(Protocol):
    """Anything with fetch_alerts(): the real Inbox, or a fake one in tests."""

    def fetch_alerts(self, after_uid: int = 0) -> Iterator[AlertEmail]: ...


@dataclass
class ImportResult:
    emails: int = 0
    listings: int = 0      # found in the emails, duplicates included
    new: int = 0           # actually added to the database
    # Subjects of emails without listings: fine for "Aktiviere dein Konto",
    # but an alert showing up here means the parser needs fixing.
    empty: list[str] = field(default_factory=list)


def run_import(inbox: AlertSource, store: ListingStore) -> ImportResult:
    result = ImportResult()
    last_uid = int(store.get_state(LAST_UID, "0"))
    for alert in inbox.fetch_alerts(after_uid=last_uid):
        listings = parse_alert(alert)
        if not listings:
            result.empty.append(f"{alert.source}: {alert.subject}")
        result.emails += 1
        result.listings += len(listings)
        result.new += sum(store.add(listing) for listing in listings)
        # Saved after every email, so a crash halfway doesn't re-read everything.
        store.set_state(LAST_UID, str(alert.uid))
    return result


def main() -> None:
    # The Windows console isn't UTF-8 by default and crashes on emoji in subjects.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_env()
    store = ListingStore()
    with Inbox() as inbox:
        result = run_import(inbox, store)
    print(f"{result.emails} new alert emails, {result.listings} listings, "
          f"{result.new} new. Database now has {store.count()} listings.")
    for subject in result.empty:
        print(f"  no listings found in: {subject}")
    store.close()


if __name__ == "__main__":
    main()
