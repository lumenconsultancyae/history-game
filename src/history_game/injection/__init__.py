"""Dependency injection composition root package."""

from history_game.injection.container import (
    CatalogServiceDep,
    GameplayServiceDep,
    ReadinessDep,
    SessionDep,
    SettingsDep,
    get_catalog_service,
    get_db_session,
    get_gameplay_service,
    verify_readiness,
)

__all__ = [
    "CatalogServiceDep",
    "GameplayServiceDep",
    "ReadinessDep",
    "SessionDep",
    "SettingsDep",
    "get_catalog_service",
    "get_db_session",
    "get_gameplay_service",
    "verify_readiness",
]
