"""Composition root binding domain ports to concrete SQLAlchemy infrastructure adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from history_game.application.services import CatalogService, GameplayService
from history_game.config.settings import Settings, get_settings
from history_game.infrastructure.persistence.database import check_database_ready
from history_game.infrastructure.persistence.repositories import (
    SqlAlchemyHistoricalEventRepository,
    SqlAlchemyTimelineSessionRepository,
)

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped AsyncSession from app.state.session_factory."""
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_catalog_service(session: SessionDep) -> CatalogService:
    """Construct CatalogService wired with SqlAlchemyHistoricalEventRepository."""
    event_repo = SqlAlchemyHistoricalEventRepository(session=session)
    return CatalogService(event_repository=event_repo)


def get_gameplay_service(session: SessionDep) -> GameplayService:
    """Construct GameplayService wired with event and session repositories."""
    event_repo = SqlAlchemyHistoricalEventRepository(session=session)
    session_repo = SqlAlchemyTimelineSessionRepository(session=session)
    return GameplayService(
        event_repository=event_repo,
        session_repository=session_repo,
    )


async def verify_readiness(session: SessionDep) -> bool:
    """Execute database readiness check via the persistence adapter."""
    return await check_database_ready(session)


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]
GameplayServiceDep = Annotated[GameplayService, Depends(get_gameplay_service)]
ReadinessDep = Annotated[bool, Depends(verify_readiness)]
