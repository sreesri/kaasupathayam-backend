from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KAASU_", extra="ignore")

    database_url: str = "postgresql+psycopg://kaasu:kaasu@localhost:5432/kaasupathayam"
    jwt_secret: str = "dev-only-insecure-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_days: int = 30
    # Google OAuth client IDs whose ID tokens we accept, as a JSON list. Only the web client ID
    # is needed: Android sign-in requests tokens for it too.
    google_client_ids: list[str] = []
    # JSON list in env, e.g. KAASU_CORS_ORIGINS='["http://localhost:8081"]'
    cors_origins: list[str] = ["http://localhost:8081", "http://localhost:19006"]

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Accept URLs as Neon/Render give them (postgres:// or postgresql://) and select the
        psycopg 3 driver; SQLAlchemy would otherwise look for psycopg2."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url


settings = Settings()
