"""Unit tests for ChronoQuest domain value objects, entities, aggregates, and events."""

from __future__ import annotations

import pytest

from history_game.domain.entities import (
    HistoricalEvent,
    PlaceHistoricalEvent,
    StartTimelineSession,
    TimelineSession,
)
from history_game.domain.events import (
    EventMisplaced,
    EventPlacedCorrectly,
    TimelineSessionCompleted,
    TimelineSessionStarted,
)
from history_game.domain.exceptions import (
    DomainError,
    InvalidGameActionError,
    InvalidHistoricalYearError,
    InvalidPlacementPositionError,
    SessionAlreadyCompletedError,
    SessionAlreadyFinishedError,
    UnexpectedEventPlacementError,
)
from history_game.domain.value_objects import (
    Difficulty,
    HistoricalEra,
    HistoricalYear,
    SessionStatus,
)


def _make_event(
    event_id: str,
    title: str,
    year: int,
    era: HistoricalEra = HistoricalEra.ANCIENT,
    region: str = "Mediterranean",
    summary: str = "A pivotal milestone in human civilization.",
    significance: str = "Transformed political and cultural institutions across regions.",
) -> HistoricalEvent:
    """Build a valid HistoricalEvent domain entity for unit tests."""
    return HistoricalEvent(
        id=event_id,
        title=title,
        year=HistoricalYear(year),
        era=era,
        region=region,
        summary=summary,
        significance=significance,
    )


def _sample_deck() -> list[HistoricalEvent]:
    """Return a deterministic 4-card deck spanning multiple eras."""
    return [
        _make_event("evt-anchor-1066", "Battle of Hastings", 1066, HistoricalEra.MEDIEVAL),
        _make_event("evt-card-44bce", "Assassination of Julius Caesar", -44, HistoricalEra.CLASSICAL),
        _make_event("evt-card-1969", "Apollo 11 Moon Landing", 1969, HistoricalEra.MODERN),
        _make_event("evt-card-3100bce", "Unification of Upper and Lower Egypt", -3100, HistoricalEra.ANCIENT),
    ]


class TestHistoricalYear:
    """Unit tests for the HistoricalYear value object."""

    def test_rejects_year_zero(self) -> None:
        """Year 0 does not exist in the historical BCE/CE calendar."""
        with pytest.raises((InvalidHistoricalYearError, ValueError)):
            HistoricalYear(0)

    @pytest.mark.parametrize("out_of_range_year", [-10001, 2101])
    def test_rejects_years_outside_supported_bounds(self, out_of_range_year: int) -> None:
        """Years outside [-10000, 2100] are rejected."""
        with pytest.raises((InvalidHistoricalYearError, ValueError)):
            HistoricalYear(out_of_range_year)

    @pytest.mark.parametrize(
        ("raw_year", "expected_label"),
        [
            (-3100, "3100 BCE"),
            (-44, "44 BCE"),
            (-1, "1 BCE"),
            (1, "1 CE"),
            (1066, "1066 CE"),
            (1969, "1969 CE"),
        ],
    )
    def test_formats_bce_and_ce_labels(self, raw_year: int, expected_label: str) -> None:
        """Negative years format as BCE and positive years format as CE."""
        year = HistoricalYear(raw_year)
        assert year.value == raw_year
        assert year.label == expected_label
        assert str(year) == expected_label

    def test_orders_chronologically_from_bce_to_ce(self) -> None:
        """Signed integer comparison orders BCE before CE chronologically."""
        y_3100_bce = HistoricalYear(-3100)
        y_44_bce = HistoricalYear(-44)
        y_1066_ce = HistoricalYear(1066)
        y_1969_ce = HistoricalYear(1969)

        assert y_3100_bce < y_44_bce < y_1066_ce < y_1969_ce
        assert y_1969_ce > y_1066_ce > y_44_bce > y_3100_bce
        assert y_44_bce <= HistoricalYear(-44)
        assert y_1066_ce >= HistoricalYear(1066)


class TestEnumsAndDifficultyConfig:
    """Unit tests for HistoricalEra, SessionStatus, and Difficulty parameters."""

    def test_historical_era_canonical_order_and_values(self) -> None:
        """All 6 canonical historical eras are present in chronological order."""
        eras = [e.value for e in HistoricalEra]
        assert eras == [
            "ancient",
            "classical",
            "medieval",
            "early_modern",
            "industrial",
            "modern",
        ]

    def test_session_status_values(self) -> None:
        """SessionStatus defines in_progress, completed, and game_over."""
        assert SessionStatus.IN_PROGRESS.value == "in_progress"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.GAME_OVER.value == "game_over"

    @pytest.mark.parametrize(
        ("difficulty", "expected_lives", "expected_cards", "expected_base_points"),
        [
            (Difficulty.EXPLORER, 3, 5, 100),
            (Difficulty.HISTORIAN, 3, 8, 150),
            (Difficulty.CHRONOMASTER, 2, 12, 200),
        ],
    )
    def test_difficulty_configuration(
        self,
        difficulty: Difficulty,
        expected_lives: int,
        expected_cards: int,
        expected_base_points: int,
    ) -> None:
        """Each difficulty tier exposes its configured lives, card count, and base points."""
        assert difficulty.initial_lives == expected_lives
        assert difficulty.cards_to_place == expected_cards
        assert difficulty.base_points == expected_base_points


class TestHistoricalEventInvariants:
    """Unit tests for HistoricalEvent entity validation."""

    def test_rejects_empty_text_fields(self) -> None:
        """HistoricalEvent requires non-empty title, region, summary, and significance."""
        with pytest.raises((DomainError, ValueError)):
            _make_event("evt-invalid", "   ", 1066)

    def test_rejects_summary_leaking_literal_year(self) -> None:
        """Clue summary must not leak the literal numeric year string."""
        with pytest.raises((DomainError, ValueError)):
            _make_event(
                "evt-spoiler",
                "Norman Conquest",
                1066,
                summary="In 1066 William the Conqueror crossed the English Channel.",
            )


class TestTimelineSessionAggregate:
    """Unit tests for TimelineSession aggregate root lifecycle and placement rules."""

    def test_starts_in_progress_with_anchor_card_and_drawn_card(self) -> None:
        """Starting a session places 1 anchor card on the timeline and draws 1 current card."""
        deck = _sample_deck()
        cmd = StartTimelineSession(
            player_name="Ada Lovelace",
            difficulty=Difficulty.EXPLORER,
            era=None,
            seed=42,
        )

        session = TimelineSession.start(cmd=cmd, deck=deck)

        assert session.player_name == "Ada Lovelace"
        assert session.difficulty == Difficulty.EXPLORER
        assert session.status == SessionStatus.IN_PROGRESS
        assert session.score == 0
        assert session.streak == 0
        assert session.max_streak == 0
        assert session.lives_remaining == 3
        assert session.initial_lives == 3
        assert session.timeline_event_ids == ["evt-anchor-1066"]
        assert session.current_event_id == "evt-card-44bce"
        assert session.remaining_deck_ids == ["evt-card-1969", "evt-card-3100bce"]
        assert session.completed_at is None

        events = session.pull_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], TimelineSessionStarted)
        assert events[0].session_id == session.id

    def test_correct_placements_build_streak_award_bonus_points_and_complete_session(self) -> None:
        """Placing all deck cards in valid slots awards base + streak bonus points and completes."""
        deck = _sample_deck()
        events_by_id = {e.id: e for e in deck}
        session = TimelineSession.start(
            cmd=StartTimelineSession(player_name="Herodotus", difficulty=Difficulty.EXPLORER),
            deck=deck,
        )
        session.pull_domain_events()  # clear start event

        # Turn 1: Place -44 before 1066 (index 0) -> streak 1, +100 pts
        attempt_1 = session.place_event(
            PlaceHistoricalEvent(
                session_id=session.id,
                event_id="evt-card-44bce",
                position_index=0,
            ),
            events_by_id=events_by_id,
        )
        assert attempt_1.is_correct is True
        assert attempt_1.submitted_position == 0
        assert attempt_1.correct_position == 0
        assert attempt_1.points_awarded == 100
        assert session.streak == 1
        assert session.max_streak == 1
        assert session.score == 100
        assert session.lives_remaining == 3
        assert session.timeline_event_ids == ["evt-card-44bce", "evt-anchor-1066"]
        assert session.current_event_id == "evt-card-1969"
        assert session.status == SessionStatus.IN_PROGRESS

        turn_1_events = session.pull_domain_events()
        assert any(isinstance(e, EventPlacedCorrectly) for e in turn_1_events)

        # Turn 2: Place 1969 after 1066 (index 2) -> streak 2, +125 pts (total 225)
        attempt_2 = session.place_event(
            PlaceHistoricalEvent(
                session_id=session.id,
                event_id="evt-card-1969",
                position_index=2,
            ),
            events_by_id=events_by_id,
        )
        assert attempt_2.is_correct is True
        assert attempt_2.points_awarded == 125
        assert session.streak == 2
        assert session.max_streak == 2
        assert session.score == 225
        assert session.timeline_event_ids == [
            "evt-card-44bce",
            "evt-anchor-1066",
            "evt-card-1969",
        ]
        assert session.current_event_id == "evt-card-3100bce"

        # Turn 3 (Final card): Place -3100 at index 0 -> streak 3, +150 pts (total 375), completed
        attempt_3 = session.place_event(
            PlaceHistoricalEvent(
                session_id=session.id,
                event_id="evt-card-3100bce",
                position_index=0,
            ),
            events_by_id=events_by_id,
        )
        assert attempt_3.is_correct is True
        assert attempt_3.points_awarded == 150
        assert session.streak == 3
        assert session.max_streak == 3
        assert session.score == 375
        assert session.timeline_event_ids == [
            "evt-card-3100bce",
            "evt-card-44bce",
            "evt-anchor-1066",
            "evt-card-1969",
        ]
        assert session.current_event_id is None
        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None

        turn_3_events = session.pull_domain_events()
        assert any(isinstance(e, EventPlacedCorrectly) for e in turn_3_events)
        assert any(isinstance(e, TimelineSessionCompleted) for e in turn_3_events)

    def test_misplacement_resets_streak_decrements_lives_inserts_at_true_slot_and_game_overs(
        self,
    ) -> None:
        """Misplacing a card resets streak, deducts a life, moves card to true slot, and triggers game_over at 0 lives."""
        deck = _sample_deck()
        events_by_id = {e.id: e for e in deck}
        session = TimelineSession.start(
            cmd=StartTimelineSession(player_name="Ibn Battuta", difficulty=Difficulty.CHRONOMASTER),
            deck=deck,
        )
        assert session.lives_remaining == 2
        session.pull_domain_events()

        # Turn 1: Misplace -44 after 1066 (submitted index 1, true chronological index 0)
        attempt_1 = session.place_event(
            PlaceHistoricalEvent(
                session_id=session.id,
                event_id="evt-card-44bce",
                position_index=1,
            ),
            events_by_id=events_by_id,
        )
        assert attempt_1.is_correct is False
        assert attempt_1.submitted_position == 1
        assert attempt_1.correct_position == 0
        assert attempt_1.points_awarded == 0
        assert session.streak == 0
        assert session.lives_remaining == 1
        # Even though misplaced, card is inserted at its true chronological slot (index 0)
        assert session.timeline_event_ids == ["evt-card-44bce", "evt-anchor-1066"]
        assert session.status == SessionStatus.IN_PROGRESS

        turn_1_events = session.pull_domain_events()
        assert any(isinstance(e, EventMisplaced) for e in turn_1_events)

        # Turn 2: Misplace 1969 at index 0 (before -44, when true chronological index is 2) -> 0 lives -> game_over
        attempt_2 = session.place_event(
            PlaceHistoricalEvent(
                session_id=session.id,
                event_id="evt-card-1969",
                position_index=0,
            ),
            events_by_id=events_by_id,
        )
        assert attempt_2.is_correct is False
        assert attempt_2.submitted_position == 0
        assert attempt_2.correct_position == 2
        assert session.lives_remaining == 0
        assert session.timeline_event_ids == [
            "evt-card-44bce",
            "evt-anchor-1066",
            "evt-card-1969",
        ]
        assert session.status == SessionStatus.GAME_OVER
        assert session.current_event_id is None
        assert session.completed_at is not None

        turn_2_events = session.pull_domain_events()
        assert any(isinstance(e, EventMisplaced) for e in turn_2_events)
        assert any(isinstance(e, TimelineSessionCompleted) for e in turn_2_events)

    def test_rejects_placement_when_session_already_finished(self) -> None:
        """Placing a card after a session is completed or game_over raises SessionAlreadyFinishedError."""
        deck = _sample_deck()[:2]  # 1 anchor + 1 card to place
        events_by_id = {e.id: e for e in deck}
        session = TimelineSession.start(
            cmd=StartTimelineSession(player_name="Hypatia", difficulty=Difficulty.EXPLORER),
            deck=deck,
        )
        session.place_event(
            PlaceHistoricalEvent(
                session_id=session.id,
                event_id="evt-card-44bce",
                position_index=0,
            ),
            events_by_id=events_by_id,
        )
        assert session.status == SessionStatus.COMPLETED

        with pytest.raises((SessionAlreadyFinishedError, SessionAlreadyCompletedError)):
            session.place_event(
                PlaceHistoricalEvent(
                    session_id=session.id,
                    event_id="evt-card-44bce",
                    position_index=0,
                ),
                events_by_id=events_by_id,
            )

    @pytest.mark.parametrize("invalid_index", [-1, 2, 99])
    def test_rejects_out_of_bounds_position_index(self, invalid_index: int) -> None:
        """Placing a card at a negative index or > len(timeline) raises InvalidPlacementPositionError."""
        deck = _sample_deck()
        events_by_id = {e.id: e for e in deck}
        session = TimelineSession.start(
            cmd=StartTimelineSession(player_name="Hypatia", difficulty=Difficulty.EXPLORER),
            deck=deck,
        )

        with pytest.raises(InvalidPlacementPositionError):
            session.place_event(
                PlaceHistoricalEvent(
                    session_id=session.id,
                    event_id="evt-card-44bce",
                    position_index=invalid_index,
                ),
                events_by_id=events_by_id,
            )

    def test_rejects_unexpected_event_id(self) -> None:
        """Submitting an event_id that does not match current_event_id raises UnexpectedEventPlacementError."""
        deck = _sample_deck()
        events_by_id = {e.id: e for e in deck}
        session = TimelineSession.start(
            cmd=StartTimelineSession(player_name="Hypatia", difficulty=Difficulty.EXPLORER),
            deck=deck,
        )

        with pytest.raises((UnexpectedEventPlacementError, InvalidGameActionError)):
            session.place_event(
                PlaceHistoricalEvent(
                    session_id=session.id,
                    event_id="evt-card-1969",
                    position_index=0,
                ),
                events_by_id=events_by_id,
            )
