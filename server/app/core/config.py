"""Runtime settings loaded from environment variables."""

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = getenv("APP_NAME", "Centralized Computer Monitoring Server")
    app_env: str = getenv("APP_ENV", "development")
    host: str = getenv("HOST", "127.0.0.1")
    port: int = int(getenv("PORT", "8000"))
    database_url: str = getenv("DATABASE_URL", "sqlite:///./monitoring.db")
    agent_registration_key: str | None = getenv("AGENT_REGISTRATION_KEY")
    agent_token_pepper: str | None = getenv("AGENT_TOKEN_PEPPER")
    metrics_retention_hours: int = int(getenv("METRICS_RETENTION_HOURS", "48"))


settings = Settings()
