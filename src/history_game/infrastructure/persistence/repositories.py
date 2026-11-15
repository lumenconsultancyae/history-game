"""SQLAlchemy repository adapters implementing domain repository ports."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from history_game.domain.entities import (
    HistoricalEvent,
    PlacementAttempt,
    TimelineSession,
)
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
from history_game.infrastructure.persistence.models import (
    HistoricalEventModel,
    PlacementAttemptModel,
    TimelineSessionModel,
)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure datetime loaded from SQLite carries UTC timezone awareness."""
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


class SqlAlchemyHistoricalEventRepository(HistoricalEventRepositoryPort):
    """SQLAlchemy async implementation of HistoricalEventRepositoryPort."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_events(
        self,
        era: HistoricalEra | None = None,
    ) -> Sequence[HistoricalEvent]:
        """Return historical events ordered chronologically by year, optionally filtered by era."""
        stmt = select(HistoricalEventModel)
        if era is not None:
            stmt = stmt.where(HistoricalEventModel.era == era.value)
        stmt = stmt.order_by(HistoricalEventModel.year.asc(), HistoricalEventModel.id.asc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def get_events_by_ids(
        self,
        event_ids: Sequence[str],
    ) -> dict[str, HistoricalEvent]:
        """Return a mapping of event_id -> HistoricalEvent for the requested IDs."""
        stmt = select(HistoricalEventModel).where(HistoricalEventModel.id.in_(list(event_ids)))
        rows = (await self._session.execute(stmt)).scalars().all()
        return {row.id: self._to_domain(row) for row in rows}

    async def count_events_by_era(self) -> dict[HistoricalEra, int]:
        """Return the number of catalog events available for each HistoricalEra."""
        counts: dict[HistoricalEra, int] = {era: 0 for era in HistoricalEra}
        stmt = select(
            HistoricalEventModel.era,
            func.count(HistoricalEventModel.id),
        ).group_by(HistoricalEventModel.era)
        for era_val, count_val in (await self._session.execute(stmt)).all():
            counts[HistoricalEra(era_val)] = int(count_val)
        return counts

    @staticmethod
    def _to_domain(row: HistoricalEventModel) -> HistoricalEvent:
        return HistoricalEvent(
            id=row.id,
            title=row.title,
            year=HistoricalYear(row.year),
            era=HistoricalEra(row.era),
            region=row.region,
            summary=row.summary,
            significance=row.significance,
        )


class SqlAlchemyTimelineSessionRepository(TimelineSessionRepositoryPort):
    """SQLAlchemy async implementation of TimelineSessionRepositoryPort."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, session: TimelineSession) -> None:
        """Persist a new or updated TimelineSession aggregate and its PlacementAttempts."""
        model = self._session_to_model(session)
        await self._session.merge(model)
        await self._session.commit()

    async def get_by_id(self, session_id: str) -> TimelineSession | None:
        """Retrieve a TimelineSession aggregate by ID or return None if not found."""
        stmt = (
            select(TimelineSessionModel)
            .where(TimelineSessionModel.id == session_id)
            .options(selectinload(TimelineSessionModel.attempts))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def list_leaderboard(
        self,
        difficulty: Difficulty | None = None,
        limit: int = 10,
    ) -> Sequence[TimelineSession]:
        """Return finished sessions ordered by score DESC, max_streak DESC, completed_at ASC."""
        stmt = (
            select(TimelineSessionModel)
            .where(
                TimelineSessionModel.status.in_(
                    [SessionStatus.COMPLETED.value, SessionStatus.GAME_OVER.value]
                )
            )
            .options(selectinload(TimelineSessionModel.attempts))
        )
        if difficulty is not None:
            stmt = stmt.where(TimelineSessionModel.difficulty == difficulty.value)

        stmt = stmt.order_by(
            TimelineSessionModel.score.desc(),
            TimelineSessionModel.max_streak.desc(),
            TimelineSessionModel.completed_at.asc(),
        ).limit(limit)

        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(row) for row in rows]

    @classmethod
    def _session_to_model(cls, session: TimelineSession) -> TimelineSessionModel:
        return TimelineSessionModel(
            id=session.id,
            player_name=session.player_name,
            difficulty=session.difficulty.value,
            era_filter=session.era_filter.value if session.era_filter is not None else None,
            status=session.status.value,
            score=session.score,
            streak=session.streak,
            max_streak=session.max_streak,
            lives_remaining=session.lives_remaining,
            initial_lives=session.initial_lives,
            timeline_event_ids_json=json.dumps(session.timeline_event_ids),
            current_event_id=session.current_event_id,
            remaining_deck_ids_json=json.dumps(session.remaining_deck_ids),
            created_at=session.created_at,
            completed_at=session.completed_at,
            attempts=[
                PlacementAttemptModel(
                    id=a.id,
                    session_id=a.session_id,
                    event_id=a.event_id,
                    submitted_position=a.submitted_position,
                    correct_position=a.correct_position,
                    is_correct=a.is_correct,
                    points_awarded=a.points_awarded,
                    streak_after=a.streak_after,
                    lives_after=a.lives_after,
                    recorded_at=a.recorded_at,
                )
                for a in session.attempts
            ],
        )

    @staticmethod
    def _to_domain(row: TimelineSessionModel) -> TimelineSession:
        return TimelineSession(
            id=row.id,
            player_name=row.player_name,
            difficulty=Difficulty(row.difficulty),
            era_filter=HistoricalEra(row.era_filter) if row.era_filter else None,
            status=SessionStatus(row.status),
            score=row.score,
            streak=row.streak,
            max_streak=row.max_streak,
            lives_remaining=row.lives_remaining,
            initial_lives=row.initial_lives,
            timeline_event_ids=list(json.loads(row.timeline_event_ids_json)),
            current_event_id=row.current_event_id,
            remaining_deck_ids=list(json.loads(row.remaining_deck_ids_json)),
            attempts=[
                PlacementAttempt(
                    id=a.id,
                    session_id=a.session_id,
                    event_id=a.event_id,
                    submitted_position=a.submitted_position,
                    correct_position=a.correct_position,
                    is_correct=a.is_correct,
                    points_awarded=a.points_awarded,
                    streak_after=a.streak_after,
                    lives_after=a.lives_after,
                    recorded_at=_ensure_utc(a.recorded_at) or datetime.now(UTC),
                )
                for a in row.attempts
            ],
            created_at=_ensure_utc(row.created_at) or datetime.now(UTC),
            completed_at=_ensure_utc(row.completed_at),
        )
