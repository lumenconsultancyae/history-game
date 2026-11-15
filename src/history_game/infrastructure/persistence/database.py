"""Database engine, Alembic migration runner, and async session factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import event, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


def _configure_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable WAL mode, foreign keys, and busy timeout on SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


def create_engine_from_url(database_url: str) -> AsyncEngine:
    """Create an AsyncEngine configured for SQLite WAL or pooled relational backends."""
    engine = create_async_engine(database_url, poolclass=NullPool)
    if database_url.startswith("sqlite"):
        event.listen(engine.sync_engine, "connect", _configure_sqlite_pragmas)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory with expire_on_commit=False."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _run_upgrade_head(connection: Connection, alembic_cfg: Config) -> None:
    """Execute Alembic upgrade to head using an existing synchronous connection."""
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")


async def run_migrations(engine: AsyncEngine) -> None:
    """Apply Alembic schema migrations up to head on the given AsyncEngine."""
    migrations_dir = Path(__file__).resolve().parents[4] / "migrations"
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    async with engine.begin() as connection:
        await connection.run_sync(_run_upgrade_head, alembic_cfg)


async def check_database_ready(session: AsyncSession) -> bool:
    """Verify database connectivity by executing a lightweight SELECT 1 query."""
    result = await session.execute(select(1))
    return bool(result.scalar_one() == 1)
