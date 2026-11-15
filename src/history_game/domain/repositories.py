"""Repository ports (interfaces) owned by the ChronoQuest domain layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from history_game.domain.entities import HistoricalEvent, TimelineSession
from history_game.domain.value_objects import Difficulty, HistoricalEra


class HistoricalEventRepositoryPort(ABC):
    """Port for querying the curated catalog of HistoricalEvent entities."""

    @abstractmethod
    async def list_events(
        self,
        era: HistoricalEra | None = None,
    ) -> Sequence[HistoricalEvent]:
        """Return historical events ordered chronologically by year, optionally filtered by era."""

    @abstractmethod
    async def get_events_by_ids(
        self,
        event_ids: Sequence[str],
    ) -> dict[str, HistoricalEvent]:
        """Return a mapping of event_id -> HistoricalEvent for the requested IDs."""

    @abstractmethod
    async def count_events_by_era(self) -> dict[HistoricalEra, int]:
        """Return the number of catalog events available for each HistoricalEra."""


class TimelineSessionRepositoryPort(ABC):
    """Port for persisting and querying TimelineSession aggregates and leaderboards."""

    @abstractmethod
    async def save(self, session: TimelineSession) -> None:
        """Persist a new or updated TimelineSession aggregate and its PlacementAttempts."""

    @abstractmethod
    async def get_by_id(self, session_id: str) -> TimelineSession | None:
        """Retrieve a TimelineSession aggregate by ID or return None if not found."""

    @abstractmethod
    async def list_leaderboard(
        self,
        difficulty: Difficulty | None = None,
        limit: int = 10,
    ) -> Sequence[TimelineSession]:
        """Return finished sessions ordered by score DESC, max_streak DESC, completed_at ASC."""
