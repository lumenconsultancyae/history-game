"""Unit tests for CatalogService and GameplayService using in-memory repository ports."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from history_game.application.services import CatalogService, GameplayService
from history_game.domain.entities import (
    HistoricalEvent,
    PlaceHistoricalEvent,
    StartTimelineSession,
    TimelineSession,
)
from history_game.domain.exceptions import EntityNotFoundError, InvalidGameActionError
from history_game.domain.repositories import (
    HistoricalEventRepositoryPort,
    TimelineSessionRepositoryPort,
)
from history_game.domain.value_objects import (
    Difficulty,
    HistoricalEra,
    HistoricalYear,
    SessionStatus,
)


class InMemoryHistoricalEventRepository(HistoricalEventRepositoryPort):
    """In-memory implementation of HistoricalEventRepositoryPort for unit testing."""

    def __init__(self, events: Sequence[HistoricalEvent]) -> None:
        self._events = list(events)

    async def list_events(self, era: HistoricalEra | None = None) -> Sequence[HistoricalEvent]:
        filtered = [e for e in self._events if era is None or e.era == era]
        return sorted(filtered, key=lambda e: (e.year.value, e.id))

    async def get_events_by_ids(
        self, event_ids: Sequence[str]
    ) -> dict[str, HistoricalEvent]:
        wanted = set(event_ids)
        return {e.id: e for e in self._events if e.id in wanted}

    async def count_events_by_era(self) -> dict[HistoricalEra, int]:
        counts: dict[HistoricalEra, int] = {era: 0 for era in HistoricalEra}
        for event in self._events:
            counts[event.era] = counts.get(event.era, 0) + 1
        return counts


class InMemoryTimelineSessionRepository(TimelineSessionRepositoryPort):
    """In-memory implementation of TimelineSessionRepositoryPort for unit testing."""

    def __init__(self) -> None:
        self._sessions: dict[str, TimelineSession] = {}

    async def save(self, session: TimelineSession) -> None:
        self._sessions[session.id] = session

    async def get_by_id(self, session_id: str) -> TimelineSession | None:
        return self._sessions.get(session_id)

    async def list_leaderboard(
        self,
        difficulty: Difficulty | None = None,
        limit: int = 10,
    ) -> Sequence[TimelineSession]:
        finished = [
            s
            for s in self._sessions.values()
            if s.status in (SessionStatus.COMPLETED, SessionStatus.GAME_OVER)
            and (difficulty is None or s.difficulty == difficulty)
        ]
        finished.sort(
            key=lambda s: (
                -s.score,
                -s.max_streak,
                s.completed_at.isoformat() if s.completed_at else "",
            )
        )
        return finished[:limit]


def _build_seed_catalog() -> list[HistoricalEvent]:
    """Create a 6-era test catalog of historical events."""
    raw = [
        ("evt-cuneiform", "Sumerian Cuneiform Writing", -3200, HistoricalEra.ANCIENT, "Mesopotamia"),
        ("evt-hammurabi", "Code of Hammurabi", -1750, HistoricalEra.ANCIENT, "Babylon"),
        ("evt-rosetta", "Rosetta Stone Decree", -196, HistoricalEra.CLASSICAL, "Egypt"),
        ("evt-paper", "Cai Lun Refines Papermaking", 105, HistoricalEra.CLASSICAL, "China"),
        ("evt-magna-carta", "Sealing of Magna Carta", 1215, HistoricalEra.MEDIEVAL, "England"),
        ("evt-printing", "Gutenberg Printing Press", 1450, HistoricalEra.EARLY_MODERN, "Germany"),
        ("evt-steam", "Watt Steam Engine", 1776, HistoricalEra.INDUSTRIAL, "Scotland"),
        ("evt-apollo", "Apollo 11 Lunar Landing", 1969, HistoricalEra.MODERN, "Space"),
    ]
    return [
        HistoricalEvent(
            id=eid,
            title=title,
            year=HistoricalYear(year),
            era=era,
            region=region,
            summary=f"Clue summary describing {title} in {region}.",
            significance=f"Historical significance explaining the impact of {title}.",
        )
        for eid, title, year, era, region in raw
    ]


class TestFakeRepositoryPortConformance:
    """Ensure in-memory test doubles conform strictly to domain repository ports."""

    def test_in_memory_repositories_match_domain_ports(self) -> None:
        """Every public method on the in-memory doubles exists on the abstract domain ports."""
        event_port_methods = {
            name for name in dir(HistoricalEventRepositoryPort) if not name.startswith("_")
        }
        event_fake_methods = {
            name for name in dir(InMemoryHistoricalEventRepository) if not name.startswith("_")
        }
        assert event_fake_methods <= event_port_methods

        session_port_methods = {
            name for name in dir(TimelineSessionRepositoryPort) if not name.startswith("_")
        }
        session_fake_methods = {
            name for name in dir(InMemoryTimelineSessionRepository) if not name.startswith("_")
        }
        assert session_fake_methods <= session_port_methods


class TestCatalogService:
    """Unit tests for CatalogService era metadata and event filtering."""

    async def test_list_eras_returns_six_chronological_eras_with_counts(self) -> None:
        """CatalogService.list_eras returns all 6 eras in chronological order with event counts."""
        repo = InMemoryHistoricalEventRepository(_build_seed_catalog())
        service = CatalogService(event_repository=repo)

        eras = await service.list_eras()

        assert len(eras) == 6
        assert [e.era for e in eras] == [
            HistoricalEra.ANCIENT,
            HistoricalEra.CLASSICAL,
            HistoricalEra.MEDIEVAL,
            HistoricalEra.EARLY_MODERN,
            HistoricalEra.INDUSTRIAL,
            HistoricalEra.MODERN,
        ]
        ancient_info = eras[0]
        assert ancient_info.event_count == 2
        assert ancient_info.start_year < ancient_info.end_year

    async def test_list_events_supports_optional_era_filter_and_chronological_order(self) -> None:
        """CatalogService.list_events orders events by year and filters by era when requested."""
        repo = InMemoryHistoricalEventRepository(_build_seed_catalog())
        service = CatalogService(event_repository=repo)

        all_events = await service.list_events()
        assert len(all_events) == 8
        assert [e.year.value for e in all_events] == sorted(e.year.value for e in all_events)

        ancient_events = await service.list_events(era=HistoricalEra.ANCIENT)
        assert len(ancient_events) == 2
        assert all(e.era == HistoricalEra.ANCIENT for e in ancient_events)
        assert [e.id for e in ancient_events] == ["evt-cuneiform", "evt-hammurabi"]


class TestGameplayService:
    """Unit tests for GameplayService session orchestration and leaderboard queries."""

    async def test_start_session_samples_deck_and_persists_session(self) -> None:
        """GameplayService.start_session creates a seeded session and saves it to the repository."""
        event_repo = InMemoryHistoricalEventRepository(_build_seed_catalog())
        session_repo = InMemoryTimelineSessionRepository()
        service = GameplayService(
            event_repository=event_repo,
            session_repository=session_repo,
        )

        result = await service.start_session(
            StartTimelineSession(
                player_name="Ada Lovelace",
                difficulty=Difficulty.EXPLORER,
                era=None,
                seed=42,
            )
        )

        session = result.session
        assert session.player_name == "Ada Lovelace"
        assert session.status == SessionStatus.IN_PROGRESS
        assert len(session.timeline_event_ids) == 1
        assert session.current_event_id is not None
        # Explorer has 5 cards to place (1 current + 4 remaining)
        assert 1 + len(session.remaining_deck_ids) == 5

        persisted = await session_repo.get_by_id(session.id)
        assert persisted is not None
        assert persisted.id == session.id

    async def test_start_session_with_insufficient_events_raises_error(self) -> None:
        """Starting a session when fewer than 2 events match the filter raises InvalidGameActionError."""
        single_event = _build_seed_catalog()[:1]
        event_repo = InMemoryHistoricalEventRepository(single_event)
        session_repo = InMemoryTimelineSessionRepository()
        service = GameplayService(
            event_repository=event_repo,
            session_repository=session_repo,
        )

        with pytest.raises(InvalidGameActionError):
            await service.start_session(
                StartTimelineSession(
                    player_name="Ada Lovelace",
                    difficulty=Difficulty.EXPLORER,
                    era=HistoricalEra.ANCIENT,
                )
            )

    async def test_get_session_raises_not_found_for_unknown_id(self) -> None:
        """GameplayService.get_session raises EntityNotFoundError when session does not exist."""
        event_repo = InMemoryHistoricalEventRepository(_build_seed_catalog())
        session_repo = InMemoryTimelineSessionRepository()
        service = GameplayService(
            event_repository=event_repo,
            session_repository=session_repo,
        )

        with pytest.raises(EntityNotFoundError):
            await service.get_session("non-existent-session-id")

    async def test_place_event_updates_session_and_records_leaderboard_upon_completion(self) -> None:
        """Placing all cards in an era-filtered session completes the run and ranks on leaderboard."""
        event_repo = InMemoryHistoricalEventRepository(_build_seed_catalog())
        session_repo = InMemoryTimelineSessionRepository()
        service = GameplayService(
            event_repository=event_repo,
            session_repository=session_repo,
        )

        # Ancient era in test catalog has 2 events: 1 anchor + 1 card to place
        started = await service.start_session(
            StartTimelineSession(
                player_name="Herodotus",
                difficulty=Difficulty.EXPLORER,
                era=HistoricalEra.ANCIENT,
                seed=7,
            )
        )
        session = started.session
        anchor_event = started.events_by_id[session.timeline_event_ids[0]]
        current_id = session.current_event_id
        assert current_id is not None
        drawn_event = started.events_by_id[current_id]

        valid_slot = 0 if drawn_event.year < anchor_event.year else 1
        placement = await service.place_event(
            PlaceHistoricalEvent(
                session_id=session.id,
                event_id=current_id,
                position_index=valid_slot,
            )
        )

        assert placement.attempt.is_correct is True
        assert placement.session.status == SessionStatus.COMPLETED
        assert placement.session.score == 100

        leaderboard = await service.get_leaderboard(difficulty=Difficulty.EXPLORER, limit=10)
        assert len(leaderboard) == 1
        assert leaderboard[0].id == session.id
        assert leaderboard[0].player_name == "Herodotus"
        assert leaderboard[0].score == 100
