"""Domain value objects and enumerations for ChronoQuest."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from history_game.domain.exceptions import InvalidHistoricalYearError
from history_game.utils import format_historical_year

MIN_SUPPORTED_YEAR = -10000
MAX_SUPPORTED_YEAR = 2100


@dataclass(frozen=True, order=True)
class HistoricalYear:
    """Immutable non-zero integer year supporting BCE (< 0) and CE (> 0) ordering."""

    value: int

    def __post_init__(self) -> None:
        if self.value == 0:
            raise InvalidHistoricalYearError(
                "Year 0 does not exist in the historical BCE/CE calendar."
            )
        if self.value < MIN_SUPPORTED_YEAR or self.value > MAX_SUPPORTED_YEAR:
            raise InvalidHistoricalYearError(
                f"Year {self.value} is outside supported bounds "
                f"[{MIN_SUPPORTED_YEAR}, {MAX_SUPPORTED_YEAR}]."
            )

    @property
    def label(self) -> str:
        """Format the signed year as 'N BCE' or 'N CE'."""
        return format_historical_year(self.value)

    def __str__(self) -> str:
        return self.label


@dataclass(frozen=True)
class _EraMeta:
    label: str
    start_year: int
    end_year: int
    period_label: str
    description: str


class HistoricalEra(StrEnum):
    """Canonical periods of world history in chronological order."""

    ANCIENT = "ancient"
    CLASSICAL = "classical"
    MEDIEVAL = "medieval"
    EARLY_MODERN = "early_modern"
    INDUSTRIAL = "industrial"
    MODERN = "modern"

    @property
    def label(self) -> str:
        """Human-readable display name for the era."""
        return _ERA_METADATA[self].label

    @property
    def start_year(self) -> int:
        """Approximate starting year of the era."""
        return _ERA_METADATA[self].start_year

    @property
    def end_year(self) -> int:
        """Approximate ending year of the era."""
        return _ERA_METADATA[self].end_year

    @property
    def period_label(self) -> str:
        """Formatted chronological range label for the era."""
        return _ERA_METADATA[self].period_label

    @property
    def description(self) -> str:
        """Concise historical summary of the era."""
        return _ERA_METADATA[self].description


_ERA_METADATA: dict[HistoricalEra, _EraMeta] = {
    HistoricalEra.ANCIENT: _EraMeta(
        label="Ancient World",
        start_year=-3500,
        end_year=-500,
        period_label="3500 BCE – 500 BCE",
        description=(
            "Early river-valley civilizations, writing systems, monumental architecture, "
            "and bronze-to-iron age empires."
        ),
    ),
    HistoricalEra.CLASSICAL: _EraMeta(
        label="Classical Era",
        start_year=-500,
        end_year=500,
        period_label="500 BCE – 500 CE",
        description=(
            "Mediterranean city-states, Hellenistic synthesis, Imperial Rome, Han statecraft, "
            "and foundational philosophical traditions."
        ),
    ),
    HistoricalEra.MEDIEVAL: _EraMeta(
        label="Medieval Era",
        start_year=500,
        end_year=1450,
        period_label="500 CE – 1450 CE",
        description=(
            "Transcontinental Silk Road networks, the Islamic Golden Age, Tang-Song innovations, "
            "and constitutional charters."
        ),
    ),
    HistoricalEra.EARLY_MODERN: _EraMeta(
        label="Early Modern Era",
        start_year=1450,
        end_year=1750,
        period_label="1450 CE – 1750 CE",
        description=(
            "Movable-type printing, global maritime voyages, Renaissance humanism, "
            "and the Scientific Revolution."
        ),
    ),
    HistoricalEra.INDUSTRIAL: _EraMeta(
        label="Industrial Age",
        start_year=1750,
        end_year=1914,
        period_label="1750 CE – 1914 CE",
        description=(
            "Steam mechanization, democratic revolutions, railway and telegraph networks, "
            "and modern germ theory."
        ),
    ),
    HistoricalEra.MODERN: _EraMeta(
        label="Modern Era",
        start_year=1914,
        end_year=2025,
        period_label="1914 CE – Present",
        description=(
            "Global geopolitics, universal human rights charters, space exploration, "
            "and the digital information revolution."
        ),
    ),
}


class SessionStatus(StrEnum):
    """Lifecycle states of a TimelineSession."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    GAME_OVER = "game_over"


class Difficulty(StrEnum):
    """Challenge difficulty tiers governing lives, deck size, and scoring."""

    EXPLORER = "explorer"
    HISTORIAN = "historian"
    CHRONOMASTER = "chronomaster"

    @property
    def initial_lives(self) -> int:
        """Number of mistakes allowed before game_over."""
        if self is Difficulty.CHRONOMASTER:
            return 2
        return 3

    @property
    def cards_to_place(self) -> int:
        """Number of drawn cards the player must place (excluding the initial anchor card)."""
        if self is Difficulty.EXPLORER:
            return 5
        if self is Difficulty.HISTORIAN:
            return 8
        return 12

    @property
    def base_points(self) -> int:
        """Base score awarded for each correct placement."""
        if self is Difficulty.EXPLORER:
            return 100
        if self is Difficulty.HISTORIAN:
            return 150
        return 200

    @property
    def streak_bonus(self) -> int:
        """Incremental bonus points per consecutive streak step beyond the first."""
        if self is Difficulty.EXPLORER:
            return 25
        if self is Difficulty.HISTORIAN:
            return 50
        return 75
