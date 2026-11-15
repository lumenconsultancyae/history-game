"""Application services orchestrating ChronoQuest catalog queries and timeline sessions."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from history_game.domain.entities import (
    EraInfo,
    HistoricalEvent,
    PlaceHistoricalEvent,
    PlacementAttempt,
    StartTimelineSession,
    TimelineSession,
)
from history_game.domain.exceptions import EntityNotFoundError, InvalidGameActionError
from history_game.domain.repositories import (
    HistoricalEventRepositoryPort,
    TimelineSessionRepositoryPort,
)
from history_game.domain.value_objects import Difficulty, HistoricalEra


@dataclass(frozen=True)
class SessionStateResult:
    """Result envelope pairing a TimelineSession aggregate with its resolved catalog events."""

    session: TimelineSession
    events_by_id: dict[str, HistoricalEvent]


@dataclass(frozen=True)
class PlacementOutcomeResult:
    """Result envelope returned after evaluating a PlaceHistoricalEvent command."""

    attempt: PlacementAttempt
    session: TimelineSession
    events_by_id: dict[str, HistoricalEvent]


class CatalogService:
    """Application service for browsing historical eras and timeline events."""

    def __init__(self, event_repository: HistoricalEventRepositoryPort) -> None:
        self._event_repository = event_repository

    async def list_eras(self) -> Sequence[EraInfo]:
        """Return all 6 canonical historical eras in chronological order with event counts."""
        counts = await self._event_repository.count_events_by_era()
        return [
            EraInfo(
                era=era,
                label=era.label,
                start_year=era.start_year,
                end_year=era.end_year,
                period_label=era.period_label,
                description=era.description,
                event_count=counts.get(era, 0),
            )
            for era in HistoricalEra
        ]

    async def list_events(
        self,
        era: HistoricalEra | None = None,
    ) -> Sequence[HistoricalEvent]:
        """Return historical events ordered chronologically, optionally filtered by era."""
        return await self._event_repository.list_events(era=era)


class GameplayService:
    """Application service orchestrating TimelineSession creation, placement, and leaderboards."""

    def __init__(
        self,
        event_repository: HistoricalEventRepositoryPort,
        session_repository: TimelineSessionRepositoryPort,
    ) -> None:
        self._event_repository = event_repository
        self._session_repository = session_repository

    async def start_session(self, cmd: StartTimelineSession) -> SessionStateResult:
        """Sample a deck of historical events and initialize a new TimelineSession."""
        available_events = list(await self._event_repository.list_events(era=cmd.era))
        if len(available_events) < 2:
            raise InvalidGameActionError(
                "At least 2 historical events are required to start a timeline session."
            )

        target_deck_size = min(len(available_events), cmd.difficulty.cards_to_place + 1)
        rng = random.Random(cmd.seed)
        deck = rng.sample(available_events, k=target_deck_size)

        session = TimelineSession.start(cmd=cmd, deck=deck)
        await self._session_repository.save(session)

        events_by_id = {event.id: event for event in deck}
        return SessionStateResult(session=session, events_by_id=events_by_id)

    async def get_session(self, session_id: str) -> SessionStateResult:
        """Retrieve an existing TimelineSession and its referenced catalog events."""
        session = await self._session_repository.get_by_id(session_id)
        if session is None:
            raise EntityNotFoundError(f"Timeline session '{session_id}' was not found.")
        events_by_id = await self._event_repository.get_events_by_ids(
            session.referenced_event_ids
        )
        return SessionStateResult(session=session, events_by_id=events_by_id)

    async def place_event(self, cmd: PlaceHistoricalEvent) -> PlacementOutcomeResult:
        """Evaluate a placement command on an active session and persist the outcome."""
        session = await self._session_repository.get_by_id(cmd.session_id)
        if session is None:
            raise EntityNotFoundError(f"Timeline session '{cmd.session_id}' was not found.")

        needed_ids = list(dict.fromkeys([*session.referenced_event_ids, cmd.event_id]))
        events_by_id = await self._event_repository.get_events_by_ids(needed_ids)

        attempt = session.place_event(cmd=cmd, events_by_id=events_by_id)
        await self._session_repository.save(session)
        return PlacementOutcomeResult(
            attempt=attempt,
            session=session,
            events_by_id=events_by_id,
        )

    async def get_leaderboard(
        self,
        difficulty: Difficulty | None = None,
        limit: int = 10,
    ) -> Sequence[TimelineSession]:
        """Return top finished timeline sessions ranked by score and streak."""
        return await self._session_repository.list_leaderboard(
            difficulty=difficulty,
            limit=limit,
        )
