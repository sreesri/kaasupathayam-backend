import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Lists read from env as either JSON (`["a","b"]`) or plain comma-separated text (`a,b` or `a`).
EnvList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KAASU_", extra="ignore")

    database_url: str = "postgresql+psycopg://kaasu:kaasu@localhost:5432/kaasupathayam"
    jwt_secret: str = "dev-only-insecure-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_days: int = 30
    # Google OAuth client IDs whose ID tokens we accept. Only the web client ID is needed:
    # Android sign-in requests tokens for it too.
    google_client_ids: EnvList = []
    cors_origins: EnvList = ["http://localhost:8081", "http://localhost:19006"]

    @field_validator("google_client_ids", "cors_origins", mode="before")
    @classmethod
    def parse_env_list(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if value.startswith("["):
            return json.loads(value)
        # Origins never end in "/", and a pasted trailing slash would break CORS matching.
        return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]

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
