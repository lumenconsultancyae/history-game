"""Modular APIRouter endpoints for ChronoQuest."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Query, status

from history_game.api.dto import (
    CreateSessionRequest,
    EraInfoResponse,
    HealthResponse,
    HistoricalEventResponse,
    LeaderboardEntryResponse,
    PlaceEventRequest,
    PlacementAttemptResponse,
    PlacementOutcomeResponse,
    RedactedEventResponse,
    TimelineSessionResponse,
)
from history_game.domain.entities import (
    HistoricalEvent,
    PlaceHistoricalEvent,
    PlacementAttempt,
    StartTimelineSession,
    TimelineSession,
)
from history_game.domain.value_objects import Difficulty, HistoricalEra
from history_game.injection.container import (
    CatalogServiceDep,
    GameplayServiceDep,
    ReadinessDep,
    SettingsDep,
)

health_router = APIRouter(tags=["health"])
catalog_router = APIRouter(prefix="/api/v1", tags=["catalog"])
sessions_router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
leaderboard_router = APIRouter(prefix="/api/v1/leaderboard", tags=["leaderboard"])


def _serialize_event(event: HistoricalEvent) -> HistoricalEventResponse:
    return HistoricalEventResponse(
        id=event.id,
        title=event.title,
        year=event.year.value,
        year_label=event.year.label,
        era=event.era,
        era_label=event.era.label,
        region=event.region,
        summary=event.summary,
        significance=event.significance,
    )


def _serialize_redacted_event(event: HistoricalEvent) -> RedactedEventResponse:
    return RedactedEventResponse(
        id=event.id,
        title=event.title,
        era=event.era,
        era_label=event.era.label,
        region=event.region,
        summary=event.summary,
    )


def _serialize_attempt(
    attempt: PlacementAttempt,
    events_by_id: Mapping[str, HistoricalEvent],
) -> PlacementAttemptResponse:
    placed = events_by_id[attempt.event_id]
    return PlacementAttemptResponse(
        id=attempt.id,
        event_id=attempt.event_id,
        placed_event=_serialize_event(placed),
        submitted_position=attempt.submitted_position,
        correct_position=attempt.correct_position,
        is_correct=attempt.is_correct,
        points_awarded=attempt.points_awarded,
        streak_after=attempt.streak_after,
        lives_after=attempt.lives_after,
        recorded_at=attempt.recorded_at,
    )


def _serialize_session(
    session: TimelineSession,
    events_by_id: Mapping[str, HistoricalEvent],
) -> TimelineSessionResponse:
    timeline_cards = [
        _serialize_event(events_by_id[eid])
        for eid in session.timeline_event_ids
        if eid in events_by_id
    ]
    current_card = (
        _serialize_redacted_event(events_by_id[session.current_event_id])
        if session.current_event_id is not None and session.current_event_id in events_by_id
        else None
    )
    attempts = [
        _serialize_attempt(attempt, events_by_id)
        for attempt in session.attempts
        if attempt.event_id in events_by_id
    ]
    return TimelineSessionResponse(
        id=session.id,
        player_name=session.player_name,
        difficulty=session.difficulty,
        era_filter=session.era_filter,
        status=session.status,
        score=session.score,
        streak=session.streak,
        max_streak=session.max_streak,
        lives_remaining=session.lives_remaining,
        initial_lives=session.initial_lives,
        cards_remaining=session.cards_remaining,
        timeline=timeline_cards,
        current_event=current_card,
        attempts=attempts,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@health_router.get("/healthz", response_model=HealthResponse)
async def healthz(settings: SettingsDep) -> HealthResponse:
    """Process liveness probe."""
    return HealthResponse(status="ok", service="history-game", version=settings.app_version)


@health_router.get("/readyz", response_model=HealthResponse)
async def readyz(settings: SettingsDep, is_ready: ReadinessDep) -> HealthResponse:
    """Service readiness probe verifying SQLite database connectivity."""
    return HealthResponse(
        status="ready" if is_ready else "degraded",
        service="history-game",
        version=settings.app_version,
    )


@catalog_router.get("/eras", response_model=list[EraInfoResponse])
async def list_eras(service: CatalogServiceDep) -> list[EraInfoResponse]:
    """List all 6 canonical historical eras in chronological order with event counts."""
    eras = await service.list_eras()
    return [
        EraInfoResponse(
            era=e.era,
            label=e.label,
            start_year=e.start_year,
            end_year=e.end_year,
            period_label=e.period_label,
            description=e.description,
            event_count=e.event_count,
        )
        for e in eras
    ]


@catalog_router.get("/events", response_model=list[HistoricalEventResponse])
async def list_events(
    service: CatalogServiceDep,
    era: Annotated[HistoricalEra | None, Query()] = None,
) -> list[HistoricalEventResponse]:
    """List historical events ordered chronologically, with optional era filter."""
    events = await service.list_events(era=era)
    return [_serialize_event(ev) for ev in events]


@sessions_router.post(
    "",
    response_model=TimelineSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    payload: CreateSessionRequest,
    service: GameplayServiceDep,
) -> TimelineSessionResponse:
    """Start a new TimelineSession with 1 face-up anchor card and 1 drawn card."""
    result = await service.start_session(
        StartTimelineSession(
            player_name=payload.player_name,
            difficulty=payload.difficulty,
            era=payload.era,
            seed=payload.seed,
        )
    )
    return _serialize_session(result.session, result.events_by_id)


@sessions_router.get("/{session_id}", response_model=TimelineSessionResponse)
async def get_session(
    session_id: str,
    service: GameplayServiceDep,
) -> TimelineSessionResponse:
    """Retrieve the current state of a TimelineSession by ID."""
    result = await service.get_session(session_id)
    return _serialize_session(result.session, result.events_by_id)


@sessions_router.post(
    "/{session_id}/placements",
    response_model=PlacementOutcomeResponse,
)
async def place_event(
    session_id: str,
    payload: PlaceEventRequest,
    service: GameplayServiceDep,
) -> PlacementOutcomeResponse:
    """Submit a chronological slot placement for the current drawn card."""
    outcome = await service.place_event(
        PlaceHistoricalEvent(
            session_id=session_id,
            event_id=payload.event_id,
            position_index=payload.position_index,
        )
    )
    return PlacementOutcomeResponse(
        attempt=_serialize_attempt(outcome.attempt, outcome.events_by_id),
        session=_serialize_session(outcome.session, outcome.events_by_id),
    )


@leaderboard_router.get("", response_model=list[LeaderboardEntryResponse])
async def get_leaderboard(
    service: GameplayServiceDep,
    difficulty: Annotated[Difficulty | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[LeaderboardEntryResponse]:
    """Return top finished timeline sessions ranked by score and streak."""
    sessions = await service.get_leaderboard(difficulty=difficulty, limit=limit)
    return [
        LeaderboardEntryResponse(
            rank=idx + 1,
            id=s.id,
            session_id=s.id,
            player_name=s.player_name,
            difficulty=s.difficulty,
            era_filter=s.era_filter,
            status=s.status,
            score=s.score,
            max_streak=s.max_streak,
            cards_placed=max(0, len(s.timeline_event_ids) - 1),
            completed_at=s.completed_at,
        )
        for idx, s in enumerate(sessions)
    ]
