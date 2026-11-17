"""Remember which listings a profile has already swiped.

Stored in the same database as the listings (see db.py), so swipes survive
restarts and both phones see the same state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .db import Database

Direction = Literal["left", "right"]  # like a Java enum, but checked by pydantic


class Swipe(BaseModel):
    listing_id: str
    direction: Direction


class SwipeStore:
    def __init__(self, target: Path | str | None = None) -> None:
        self.db = Database(target)

    def record(self, profile_id: str, swipe: Swipe) -> None:
        # Delete first so a repeated swipe counts as the newest one
        self.remove(profile_id, swipe.listing_id)
        self.db.execute(
            "INSERT INTO swipes (profile_id, listing_id, direction) VALUES (?, ?, ?)",
            (profile_id, swipe.listing_id, swipe.direction),
        )

    def swiped_ids(self, profile_id: str) -> set[str]:
        rows = self.db.execute("SELECT listing_id FROM swipes WHERE profile_id = ?", (profile_id,))
        return {listing_id for (listing_id,) in rows}

    def all(self, profile_id: str) -> list[Swipe]:
        """All swipes of a profile, oldest first."""
        rows = self.db.execute(
            "SELECT listing_id, direction FROM swipes WHERE profile_id = ? ORDER BY seq",
            (profile_id,),
        )
        return [Swipe(listing_id=lid, direction=d) for lid, d in rows]

    def right_ids(self, profile_id: str) -> list[str]:
        """Listings swiped right, newest first."""
        rows = self.db.execute(
            "SELECT listing_id FROM swipes WHERE profile_id = ? AND direction = 'right' "
            "ORDER BY seq DESC",
            (profile_id,),
        )
        return [listing_id for (listing_id,) in rows]

    def remove(self, profile_id: str, listing_id: str) -> bool:
        """Undo one swipe. Returns False if there was nothing to undo."""
        cursor = self.db.execute(
            "DELETE FROM swipes WHERE profile_id = ? AND listing_id = ?", (profile_id, listing_id))
        return cursor.rowcount > 0

    def reset(self, profile_id: str) -> None:
        self.db.execute("DELETE FROM swipes WHERE profile_id = ?", (profile_id,))

    def close(self) -> None:
        self.db.close()
