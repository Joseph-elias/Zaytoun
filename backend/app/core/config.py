from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Worker Radar API"
    database_url: str = "sqlite:///./worker_radar.db"
    db_fallback_url: str = "sqlite:///./worker_radar.db"

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
