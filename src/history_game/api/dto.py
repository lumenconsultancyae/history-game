"""Pydantic v2 request and response DTOs for the ChronoQuest REST API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from history_game.domain.value_objects import Difficulty, HistoricalEra, SessionStatus


class HealthResponse(BaseModel):
    """Liveness and readiness probe response payload."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    status: str = Field(default="ok")
    service: str = Field(default="history-game")
    version: str = Field(default="0.1.0")


class EraInfoResponse(BaseModel):
    """Metadata and event count for a canonical HistoricalEra."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    era: HistoricalEra
    label: str
    start_year: int
    end_year: int
    period_label: str
    description: str
    event_count: int


class HistoricalEventResponse(BaseModel):
    """Revealed historical event card with year and historical significance."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    title: str
    year: int
    year_label: str
    era: HistoricalEra
    era_label: str
    region: str
    summary: str
    significance: str


class RedactedEventResponse(BaseModel):
    """Drawn historical event card with its year and significance redacted until placed."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    title: str
    era: HistoricalEra
    era_label: str
    region: str
    summary: str


class CreateSessionRequest(BaseModel):
    """Request payload for starting a new TimelineSession."""

    model_config = ConfigDict(extra="forbid")

    player_name: str = Field(min_length=1, max_length=64)
    difficulty: Difficulty = Field(default=Difficulty.EXPLORER)
    era: HistoricalEra | None = Field(default=None)
    seed: int | None = Field(default=None)


class PlaceEventRequest(BaseModel):
    """Request payload for submitting a chronological slot placement."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    position_index: int


class PlacementAttemptResponse(BaseModel):
    """Serialized PlacementAttempt with the revealed HistoricalEvent details."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    event_id: str
    placed_event: HistoricalEventResponse
    submitted_position: int
    correct_position: int
    is_correct: bool
    points_awarded: int
    streak_after: int
    lives_after: int
    recorded_at: datetime


class TimelineSessionResponse(BaseModel):
    """Serialized TimelineSession state including timeline cards, drawn card, and attempts."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    player_name: str
    difficulty: Difficulty
    era_filter: HistoricalEra | None
    status: SessionStatus
    score: int
    streak: int
    max_streak: int
    lives_remaining: int
    initial_lives: int
    cards_remaining: int
    timeline: list[HistoricalEventResponse]
    current_event: RedactedEventResponse | None
    attempts: list[PlacementAttemptResponse] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None


class PlacementOutcomeResponse(BaseModel):
    """Response returned after evaluating a placement attempt on an active session."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    attempt: PlacementAttemptResponse
    session: TimelineSessionResponse


class LeaderboardEntryResponse(BaseModel):
    """Ranked Hall of Records entry for a finished TimelineSession."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    rank: int
    id: str
    session_id: str
    player_name: str
    difficulty: Difficulty
    era_filter: HistoricalEra | None
    status: SessionStatus
    score: int
    max_streak: int
    cards_placed: int
    completed_at: datetime | None
