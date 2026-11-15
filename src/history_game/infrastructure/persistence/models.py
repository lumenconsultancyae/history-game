"""SQLAlchemy 2.0 declarative ORM models with deterministic naming conventions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, MetaData, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base with portable constraint naming conventions."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class HistoricalEventModel(Base):
    """ORM model for curated historical timeline events."""

    __tablename__ = "historical_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    era: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    significance: Mapped[str] = mapped_column(Text, nullable=False)


class TimelineSessionModel(Base):
    """ORM model for a player's timeline placement game session."""

    __tablename__ = "timeline_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    player_name: Mapped[str] = mapped_column(String(64), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    era_filter: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lives_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_lives: Mapped[int] = mapped_column(Integer, nullable=False)
    timeline_event_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    current_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remaining_deck_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    attempts: Mapped[list[PlacementAttemptModel]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PlacementAttemptModel.recorded_at.asc()",
    )


class PlacementAttemptModel(Base):
    """ORM model recording a single card placement turn within a TimelineSession."""

    __tablename__ = "placement_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("timeline_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("historical_events.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    submitted_position: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    streak_after: Mapped[int] = mapped_column(Integer, nullable=False)
    lives_after: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped[TimelineSessionModel] = relationship(back_populates="attempts")
