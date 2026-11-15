"""FastAPI application factory and ASGI lifespan handler."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from history_game.api.errors import register_exception_handlers
from history_game.api.routes import (
    catalog_router,
    health_router,
    leaderboard_router,
    sessions_router,
)
from history_game.config.settings import Settings, get_settings
from history_game.infrastructure.persistence.database import (
    create_engine_from_url,
    create_session_factory,
    run_migrations,
)
from history_game.infrastructure.persistence.seed_data import seed_catalog_if_empty


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct the FastAPI application with lifespan-managed migrations and seed data."""
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine_from_url(active_settings.database_url)
        session_factory = create_session_factory(engine)
        await run_migrations(engine)
        if active_settings.seed_on_startup:
            await seed_catalog_if_empty(session_factory)
        app.state.engine = engine
        app.state.session_factory = session_factory
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(sessions_router)
    app.include_router(leaderboard_router)

    static_path = Path(active_settings.static_dir)
    if not static_path.is_dir() and active_settings.static_dir == "frontend/dist":
        fallback_static = Path(__file__).resolve().parents[3] / "frontend" / "dist"
        if fallback_static.is_dir():
            static_path = fallback_static
    if static_path.is_dir():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="frontend")

    return app


app = create_app()
