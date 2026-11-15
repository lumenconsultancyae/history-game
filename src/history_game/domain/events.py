"""Domain events emitted by ChronoQuest gameplay state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from history_game.domain.value_objects import Difficulty, SessionStatus


@dataclass(frozen=True)
class DomainEvent:
    """Base immutable domain event."""

    occurred_at: datetime


@dataclass(frozen=True)
class TimelineSessionStarted(DomainEvent):
    """Emitted when a TimelineSession is initialized with an anchor card and drawn card."""

    session_id: str
    player_name: str
    difficulty: Difficulty
    anchor_event_id: str
    current_event_id: str


@dataclass(frozen=True)
class EventPlacedCorrectly(DomainEvent):
    """Emitted when a player places the drawn event in a valid chronological slot."""

    session_id: str
    attempt_id: str
    event_id: str
    position_index: int
    points_awarded: int
    streak: int
    score: int


@dataclass(frozen=True)
class EventMisplaced(DomainEvent):
    """Emitted when a player places the drawn event in an invalid chronological slot."""

    session_id: str
    attempt_id: str
    event_id: str
    submitted_position: int
    correct_position: int
    lives_remaining: int


@dataclass(frozen=True)
class TimelineSessionCompleted(DomainEvent):
    """Emitted when a TimelineSession reaches completed or game_over status."""

    session_id: str
    status: SessionStatus
    final_score: int
    max_streak: int
    lives_remaining: int
