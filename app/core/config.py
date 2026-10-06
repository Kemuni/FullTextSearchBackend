from pathlib import Path

from pydantic import FilePath, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str
    DATABASE_URL: PostgresDsn

    ELASTICSEARCH_URL: str
    ELASTICSEARCH_PASSWORD: str
    REDIS_URL: str

    POST_CACHE_TTL_SECONDS: int = 60
    READ_RATE_LIMIT: int = 120
    WRITE_RATE_LIMIT: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    INIT_DATA_PATH: FilePath = Path("init_data", "posts.csv")
    OUTBOX_BATCH_SIZE: int = 100
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_asyncpg_driver(cls, value: str | PostgresDsn) -> str:
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+asyncpg://", 1)
        return database_url


settings = Settings()
