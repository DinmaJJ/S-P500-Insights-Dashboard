from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API Keys
    fmp_api_key: str = ""
    tiingo_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://sp500:sp500_secret@localhost:5432/sp500_insight"
    database_url_sync: str = "postgresql://sp500:sp500_secret@localhost:5432/sp500_insight"

    # App
    secret_key: str = "dev-secret-change-me"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
