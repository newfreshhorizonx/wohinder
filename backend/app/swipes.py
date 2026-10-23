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
        profile_swipes = self._swipes.setdefault(profile_id, {})
        # dicts keep insertion order; pop first so a repeated swipe counts as newest
        profile_swipes.pop(swipe.listing_id, None)
        profile_swipes[swipe.listing_id] = swipe.direction

    def swiped_ids(self, profile_id: str) -> set[str]:
        return set(self._swipes.get(profile_id, {}))

    def all(self, profile_id: str) -> list[Swipe]:
        return [Swipe(listing_id=lid, direction=d)
                for lid, d in self._swipes.get(profile_id, {}).items()]

    def right_ids(self, profile_id: str) -> list[str]:
        """Listings swiped right, newest first."""
        right = [lid for lid, d in self._swipes.get(profile_id, {}).items() if d == "right"]
        return right[::-1]  # [::-1] = reversed copy of the list

    def remove(self, profile_id: str, listing_id: str) -> bool:
        """Undo one swipe. Returns False if there was nothing to undo."""
        return self._swipes.get(profile_id, {}).pop(listing_id, None) is not None

    def reset(self, profile_id: str) -> None:
        self._swipes.pop(profile_id, None)
