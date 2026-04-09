from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_URL = f"sqlite:///{(BASE_DIR / 'worker_radar.db').as_posix()}"


class Settings(BaseSettings):
    app_name: str = "Worker Radar API"
    database_url: str = DEFAULT_SQLITE_URL
    db_fallback_url: str = DEFAULT_SQLITE_URL

    # Optional Supabase/PostgreSQL values for later deployment wiring.
    supabase_db_host: str | None = None
    supabase_db_port: int = 5432
    supabase_db_name: str | None = None
    supabase_db_user: str | None = None
    supabase_db_password: str | None = None
    supabase_db_sslmode: str = "require"

    # Auth config
    auth_secret_key: str = "change-me-in-production"
    auth_algorithm: str = "HS256"
    agro_copilot_api_base_url: str | None = None
    agro_copilot_api_key: str | None = None
    agro_copilot_timeout_seconds: int = 120
    agro_copilot_max_retries: int = 2
    agro_copilot_retry_backoff_ms: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def resolved_database_url(self) -> str:
        if self.database_url and self.database_url != self.db_fallback_url:
            return self.database_url

        if all(
            [
                self.supabase_db_host,
                self.supabase_db_name,
                self.supabase_db_user,
                self.supabase_db_password,
            ]
        ):
            return (
                f"postgresql+psycopg://{self.supabase_db_user}:{self.supabase_db_password}"
                f"@{self.supabase_db_host}:{self.supabase_db_port}/{self.supabase_db_name}"
                f"?sslmode={self.supabase_db_sslmode}"
            )

        return self.db_fallback_url


settings = Settings()
