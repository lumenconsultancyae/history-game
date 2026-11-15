"""Typed domain exceptions mapped to RFC 9457 ProblemDetails at the API boundary."""

from __future__ import annotations


class DomainError(Exception):
    """Base exception for all ChronoQuest domain errors."""

    def __init__(self, message: str, code: str = "domain_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class EntityNotFoundError(DomainError):
    """Raised when a requested era, event, or timeline session does not exist."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="entity_not_found")


class InvalidHistoricalYearError(DomainError, ValueError):
    """Raised when a HistoricalYear is 0 or outside the supported calendar range."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="invalid_historical_year")


class InvalidGameActionError(DomainError):
    """Raised when a gameplay action violates session or catalog invariants."""

    def __init__(self, message: str, code: str = "invalid_game_action") -> None:
        super().__init__(message=message, code=code)


class InvalidPlacementPositionError(InvalidGameActionError):
    """Raised when a placement position_index is outside [0, len(timeline)]."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="invalid_placement_position")


class UnexpectedEventPlacementError(InvalidGameActionError):
    """Raised when a submitted event_id does not match the session's current_event_id."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="unexpected_event_placement")


class SessionAlreadyCompletedError(InvalidGameActionError):
    """Raised when attempting to place an event on a completed or game_over session."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="session_already_completed")


class SessionAlreadyFinishedError(SessionAlreadyCompletedError):
    """Alias subclass for finished timeline sessions (completed or game_over)."""
