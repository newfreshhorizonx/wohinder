"""Read alert emails from the app inbox over IMAP. Read-only: nothing is marked or deleted."""

from __future__ import annotations

import email
import imaplib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime

IMAP_HOST = "imap.gmail.com"
FOLDER = "INBOX"

# Part of the sender address per source. IMAP's FROM search matches substrings,
# so "kleinanzeigen.de" also catches e.g. "noreply@mail.kleinanzeigen.de".
SENDERS = {
    "wg-gesucht": "wg-gesucht.de",
    "kleinanzeigen": "kleinanzeigen.de",
}


@dataclass
class AlertEmail:
    uid: int           # IMAP UID, grows with every new email in the folder
    source: str        # key of SENDERS
    subject: str
    received: datetime | None
    html: str
    text: str


def _decode_header(value: str | None) -> str:
    """'=?utf-8?q?Neue_Angebote?=' -> 'Neue Angebote'."""
    return str(make_header(decode_header(value or "")))


def _bodies(msg: Message) -> tuple[str, str]:
    """Return (html, plain text) of an email; either may be empty."""
    html, text = "", ""
    for part in msg.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if part.get_content_type() == "text/html" and not html:
            html = content
        elif part.get_content_type() == "text/plain" and not text:
            text = content
    return html, text


def parse_message(uid: int, source: str, raw: bytes) -> AlertEmail:
    msg = email.message_from_bytes(raw)
    try:
        received = parsedate_to_datetime(msg["Date"]) if msg["Date"] else None
    except (TypeError, ValueError):
        received = None
    html, text = _bodies(msg)
    return AlertEmail(uid=uid, source=source, subject=_decode_header(msg["Subject"]),
                      received=received, html=html, text=text)


class Inbox:
    """Use as `with Inbox() as inbox:`; logs in on enter and out on exit."""

    def __init__(self, user: str | None = None, password: str | None = None,
                 host: str = IMAP_HOST) -> None:
        self.user = user or os.environ["INBOX_EMAIL"]
        # Google shows app passwords with spaces; IMAP wants them without.
        self.password = (password or os.environ["INBOX_APP_PASSWORD"]).replace(" ", "")
        self.host = host
        self.conn: imaplib.IMAP4_SSL | None = None

    def __enter__(self) -> Inbox:
        self.conn = imaplib.IMAP4_SSL(self.host)
        self.conn.login(self.user, self.password)
        self.conn.select(FOLDER, readonly=True)
        return self

    def __exit__(self, *exc_info) -> None:
        if self.conn is not None:
            self.conn.logout()
            self.conn = None

    def fetch_alerts(self, after_uid: int = 0) -> Iterator[AlertEmail]:
        """Yield every alert email with a UID greater than `after_uid`, oldest first."""
        assert self.conn is not None, "use Inbox inside a `with` block"
        found: list[tuple[int, str]] = []
        for source, sender in SENDERS.items():
            _, data = self.conn.uid("SEARCH", None, f'(FROM "{sender}" UID {after_uid + 1}:*)')
            # "UID n:*" always matches the newest email, even if its UID is < n.
            found += [(int(uid), source) for uid in data[0].split() if int(uid) > after_uid]

        for uid, source in sorted(found):
            _, data = self.conn.uid("FETCH", str(uid), "(BODY.PEEK[])")
            yield parse_message(uid, source, data[0][1])
