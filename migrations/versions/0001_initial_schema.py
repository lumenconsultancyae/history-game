"""Initial schema creating historical_events, timeline_sessions, and placement_attempts.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-15 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial ChronoQuest tables and indexes."""
    op.create_table(
        "historical_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("era", sa.String(length=32), nullable=False),
        sa.Column("region", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("significance", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historical_events")),
    )
    with op.batch_alter_table("historical_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_historical_events_era"), ["era"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_historical_events_year"), ["year"], unique=False
        )

    op.create_table(
        "timeline_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("player_name", sa.String(length=64), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("era_filter", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("streak", sa.Integer(), nullable=False),
        sa.Column("max_streak", sa.Integer(), nullable=False),
        sa.Column("lives_remaining", sa.Integer(), nullable=False),
        sa.Column("initial_lives", sa.Integer(), nullable=False),
        sa.Column("timeline_event_ids_json", sa.Text(), nullable=False),
        sa.Column("current_event_id", sa.String(length=64), nullable=True),
        sa.Column("remaining_deck_ids_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_timeline_sessions")),
    )
    with op.batch_alter_table("timeline_sessions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_timeline_sessions_difficulty"), ["difficulty"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_timeline_sessions_score"), ["score"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_timeline_sessions_status"), ["status"], unique=False
        )

    op.create_table(
        "placement_attempts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("submitted_position", sa.Integer(), nullable=False),
        sa.Column("correct_position", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column("streak_after", sa.Integer(), nullable=False),
        sa.Column("lives_after", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["historical_events.id"],
            name=op.f("fk_placement_attempts_event_id_historical_events"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["timeline_sessions.id"],
            name=op.f("fk_placement_attempts_session_id_timeline_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_placement_attempts")),
    )
    with op.batch_alter_table("placement_attempts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_placement_attempts_event_id"), ["event_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_placement_attempts_session_id"), ["session_id"], unique=False
        )


def downgrade() -> None:
    """Drop placement_attempts, timeline_sessions, and historical_events tables."""
    with op.batch_alter_table("placement_attempts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_placement_attempts_session_id"))
        batch_op.drop_index(batch_op.f("ix_placement_attempts_event_id"))
    op.drop_table("placement_attempts")

    with op.batch_alter_table("timeline_sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_timeline_sessions_status"))
        batch_op.drop_index(batch_op.f("ix_timeline_sessions_score"))
        batch_op.drop_index(batch_op.f("ix_timeline_sessions_difficulty"))
    op.drop_table("timeline_sessions")

    with op.batch_alter_table("historical_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_historical_events_year"))
        batch_op.drop_index(batch_op.f("ix_historical_events_era"))
    op.drop_table("historical_events")
