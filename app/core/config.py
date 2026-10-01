from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str
    DATABASE_URL: PostgresDsn

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_asyncpg_driver(cls, value: str | PostgresDsn) -> str:
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+asyncpg://", 1)
        return database_url


settings = Settings()