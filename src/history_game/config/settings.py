"""Typed application settings leaf module."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed environment settings for ChronoQuest."""

    model_config = SettingsConfigDict(
        env_prefix="HISTORY_GAME_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "ChronoQuest: History Game"
    app_version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///./history_game.db"
    static_dir: str = "frontend/dist"
    seed_on_startup: bool = True
    default_questions_per_session: int = 5


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
