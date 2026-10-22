"""Remember which listings a profile has already swiped.

Kept in memory for now: restarting the server forgets all swipes. That's fine
while we test with fake listings. Once M2 brings the SQLite database, swipes
move there and this class keeps the same methods.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Direction = Literal["left", "right"]  # like a Java enum, but checked by pydantic


class Swipe(BaseModel):
    listing_id: str
    direction: Direction


class SwipeStore:
    def __init__(self) -> None:
        # profile_id -> {listing_id -> direction}
        self._swipes: dict[str, dict[str, Direction]] = {}

    def record(self, profile_id: str, swipe: Swipe) -> None:
        # setdefault: get the inner dict, creating it first if it's missing
        self._swipes.setdefault(profile_id, {})[swipe.listing_id] = swipe.direction

    def swiped_ids(self, profile_id: str) -> set[str]:
        return set(self._swipes.get(profile_id, {}))

    def all(self, profile_id: str) -> list[Swipe]:
        return [Swipe(listing_id=lid, direction=d)
                for lid, d in self._swipes.get(profile_id, {}).items()]

    def reset(self, profile_id: str) -> None:
        self._swipes.pop(profile_id, None)
