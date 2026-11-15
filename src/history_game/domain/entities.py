"""Domain entities, commands, and aggregate roots for ChronoQuest."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from history_game.domain.events import (
    DomainEvent,
    EventMisplaced,
    EventPlacedCorrectly,
    TimelineSessionCompleted,
    TimelineSessionStarted,
)
from history_game.domain.exceptions import (
    DomainError,
    InvalidGameActionError,
    InvalidPlacementPositionError,
    SessionAlreadyFinishedError,
    UnexpectedEventPlacementError,
)
from history_game.domain.value_objects import (
    Difficulty,
    HistoricalEra,
    HistoricalYear,
    SessionStatus,
)


@dataclass(frozen=True)
class EraInfo:
    """Read-model value object summarizing a HistoricalEra and its catalog event count."""

    era: HistoricalEra
    label: str
    start_year: int
    end_year: int
    period_label: str
    description: str
    event_count: int


@dataclass(frozen=True)
class HistoricalEvent:
    """Aggregate root in the HistoricalCatalog context representing a historical milestone."""

    id: str
    title: str
    year: HistoricalYear
    era: HistoricalEra
    region: str
    summary: str
    significance: str

    def __post_init__(self) -> None:
        if (
            not self.id.strip()
            or not self.title.strip()
            or not self.region.strip()
            or not self.summary.strip()
            or not self.significance.strip()
        ):
            raise DomainError(
                "HistoricalEvent requires non-empty id, title, region, summary, and significance."
            )
        year_token = str(abs(self.year.value))
        if re.search(rf"\b{re.escape(year_token)}\b", self.summary):
            raise DomainError(
                f"HistoricalEvent summary for '{self.id}' must not leak literal year {year_token}."
            )


@dataclass(frozen=True)
class StartTimelineSession:
    """Command requesting creation of a new TimelineSession."""

    player_name: str
    difficulty: Difficulty = Difficulty.EXPLORER
    era: HistoricalEra | None = None
    seed: int | None = None


@dataclass(frozen=True)
class PlaceHistoricalEvent:
    """Command submitting a chronological slot placement for the current drawn event."""

    session_id: str
    event_id: str
    position_index: int


@dataclass(frozen=True)
class PlacementAttempt:
    """Child entity recording a single card placement turn within a TimelineSession."""

    id: str
    session_id: str
    event_id: str
    submitted_position: int
    correct_position: int
    is_correct: bool
    points_awarded: int
    streak_after: int
    lives_after: int
    recorded_at: datetime


@dataclass
class TimelineSession:
    """Aggregate root governing one player's timeline placement challenge session."""

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
    timeline_event_ids: list[str]
    current_event_id: str | None
    remaining_deck_ids: list[str]
    attempts: list[PlacementAttempt] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    _domain_events: list[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def start(
        cls,
        cmd: StartTimelineSession,
        deck: Sequence[HistoricalEvent],
    ) -> TimelineSession:
        """Initialize a new in-progress TimelineSession with 1 anchor card and 1 drawn card."""
        cleaned_name = cmd.player_name.strip()
        if not (1 <= len(cleaned_name) <= 64):
            raise InvalidGameActionError("Player name must be between 1 and 64 characters.")
        if len(deck) < 2:
            raise InvalidGameActionError(
                "At least 2 historical events are required to start a timeline session."
            )

        session_id = str(uuid4())
        now = datetime.now(UTC)
        anchor_id = deck[0].id
        current_id = deck[1].id
        remaining_ids = [event.id for event in deck[2:]]
        initial_lives = cmd.difficulty.initial_lives

        session = cls(
            id=session_id,
            player_name=cleaned_name,
            difficulty=cmd.difficulty,
            era_filter=cmd.era,
            status=SessionStatus.IN_PROGRESS,
            score=0,
            streak=0,
            max_streak=0,
            lives_remaining=initial_lives,
            initial_lives=initial_lives,
            timeline_event_ids=[anchor_id],
            current_event_id=current_id,
            remaining_deck_ids=remaining_ids,
            attempts=[],
            created_at=now,
            completed_at=None,
        )
        session._domain_events.append(
            TimelineSessionStarted(
                occurred_at=now,
                session_id=session_id,
                player_name=cleaned_name,
                difficulty=cmd.difficulty,
                anchor_event_id=anchor_id,
                current_event_id=current_id,
            )
        )
        return session

    def place_event(
        self,
        cmd: PlaceHistoricalEvent,
        events_by_id: Mapping[str, HistoricalEvent],
    ) -> PlacementAttempt:
        """Evaluate a placement command, update score/streak/lives, and advance the deck."""
        if self.status != SessionStatus.IN_PROGRESS or self.current_event_id is None:
            raise SessionAlreadyFinishedError(
                f"Timeline session '{self.id}' is already {self.status.value} and cannot accept placements."
            )
        if cmd.event_id != self.current_event_id:
            raise UnexpectedEventPlacementError(
                f"Expected placement for current event '{self.current_event_id}', "
                f"but received '{cmd.event_id}'."
            )
        if cmd.position_index < 0 or cmd.position_index > len(self.timeline_event_ids):
            raise InvalidPlacementPositionError(
                f"Placement position_index {cmd.position_index} is out of valid bounds "
                f"[0, {len(self.timeline_event_ids)}]."
            )

        target_event = events_by_id.get(cmd.event_id)
        if target_event is None:
            raise InvalidGameActionError(f"Historical event '{cmd.event_id}' was not found.")

        timeline_years = [events_by_id[eid].year.value for eid in self.timeline_event_ids]
        target_year = target_event.year.value

        left_ok = (cmd.position_index == 0) or (
            timeline_years[cmd.position_index - 1] <= target_year
        )
        right_ok = (cmd.position_index == len(timeline_years)) or (
            target_year <= timeline_years[cmd.position_index]
        )
        is_correct = left_ok and right_ok

        if is_correct:
            correct_position = cmd.position_index
        else:
            correct_position = len(timeline_years)
            for idx, placed_year in enumerate(timeline_years):
                if target_year < placed_year:
                    correct_position = idx
                    break

        self.timeline_event_ids.insert(correct_position, cmd.event_id)

        now = datetime.now(UTC)
        attempt_id = str(uuid4())

        if is_correct:
            self.streak += 1
            self.max_streak = max(self.max_streak, self.streak)
            points_awarded = (
                self.difficulty.base_points
                + (self.streak - 1) * self.difficulty.streak_bonus
            )
            self.score += points_awarded
            self._domain_events.append(
                EventPlacedCorrectly(
                    occurred_at=now,
                    session_id=self.id,
                    attempt_id=attempt_id,
                    event_id=cmd.event_id,
                    position_index=cmd.position_index,
                    points_awarded=points_awarded,
                    streak=self.streak,
                    score=self.score,
                )
            )
        else:
            self.streak = 0
            self.lives_remaining -= 1
            points_awarded = 0
            self._domain_events.append(
                EventMisplaced(
                    occurred_at=now,
                    session_id=self.id,
                    attempt_id=attempt_id,
                    event_id=cmd.event_id,
                    submitted_position=cmd.position_index,
                    correct_position=correct_position,
                    lives_remaining=self.lives_remaining,
                )
            )

        if self.lives_remaining <= 0:
            self.status = SessionStatus.GAME_OVER
            self.current_event_id = None
            self.completed_at = now
            self._domain_events.append(
                TimelineSessionCompleted(
                    occurred_at=now,
                    session_id=self.id,
                    status=self.status,
                    final_score=self.score,
                    max_streak=self.max_streak,
                    lives_remaining=self.lives_remaining,
                )
            )
        elif not self.remaining_deck_ids:
            self.status = SessionStatus.COMPLETED
            self.current_event_id = None
            self.completed_at = now
            self._domain_events.append(
                TimelineSessionCompleted(
                    occurred_at=now,
                    session_id=self.id,
                    status=self.status,
                    final_score=self.score,
                    max_streak=self.max_streak,
                    lives_remaining=self.lives_remaining,
                )
            )
        else:
            self.current_event_id = self.remaining_deck_ids.pop(0)

        attempt = PlacementAttempt(
            id=attempt_id,
            session_id=self.id,
            event_id=cmd.event_id,
            submitted_position=cmd.position_index,
            correct_position=correct_position,
            is_correct=is_correct,
            points_awarded=points_awarded,
            streak_after=self.streak,
            lives_after=self.lives_remaining,
            recorded_at=now,
        )
        self.attempts.append(attempt)
        return attempt

    @property
    def cards_remaining(self) -> int:
        """Return total unplaced cards remaining in the session (including current drawn card)."""
        current_count = 1 if self.current_event_id is not None else 0
        return current_count + len(self.remaining_deck_ids)

    @property
    def referenced_event_ids(self) -> list[str]:
        """Return all unique event IDs referenced by this session."""
        ids: list[str] = list(self.timeline_event_ids)
        if self.current_event_id is not None:
            ids.append(self.current_event_id)
        ids.extend(self.remaining_deck_ids)
        for attempt in self.attempts:
            ids.append(attempt.event_id)
        return list(dict.fromkeys(ids))

    def pull_domain_events(self) -> list[DomainEvent]:
        """Return and clear accumulated domain events."""
        emitted = list(self._domain_events)
        self._domain_events.clear()
        return emitted
