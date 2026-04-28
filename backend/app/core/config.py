from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_URL = f"sqlite:///{(BASE_DIR / 'worker_radar.db').as_posix()}"


class Settings(BaseSettings):
    app_name: str = "Worker Radar API"
    app_env: str = "development"  # development | staging | production
    database_url: str = DEFAULT_SQLITE_URL
    db_fallback_url: str = DEFAULT_SQLITE_URL
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    cors_allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5500,http://localhost:5500"
    startup_fail_fast_validation: bool = True

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
    auth_consent_version: str = "2026-04-13"
    auth_password_reset_dev_mode: bool = False
    auth_password_reset_code_ttl_minutes: int = 15
    auth_password_reset_max_attempts: int = 5
    auth_password_reset_email_enabled: bool = False
    auth_login_lockout_enabled: bool = True
    auth_login_max_attempts: int = 5
    auth_login_lockout_minutes: int = 15
    auth_mfa_totp_issuer: str = "Zaytoun"
    auth_mfa_totp_digits: int = 6
    auth_mfa_totp_period_seconds: int = 30
    auth_mfa_totp_valid_window: int = 1
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "Zaytoun"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    agro_copilot_api_base_url: str | None = None
    agro_copilot_api_key: str | None = None
    agro_copilot_timeout_seconds: int = 120
    agro_copilot_max_retries: int = 2
    agro_copilot_retry_backoff_ms: int = 300

    # HTTP security headers
    security_hsts_enabled: bool = False
    security_hsts_max_age_seconds: int = 31536000
    security_hsts_include_subdomains: bool = True
    security_hsts_preload: bool = False
    security_trusted_hosts: str = ""
    security_content_security_policy: str = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https: http:; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    security_content_security_policy_report_only: bool = False
    security_cross_origin_opener_policy: str = "same-origin"
    security_cross_origin_resource_policy: str = "same-origin"
    security_cross_origin_embedder_policy: str = "unsafe-none"
    security_x_dns_prefetch_control: str = "off"
    request_id_header_name: str = "X-Request-ID"
    security_content_security_policy_report_uri: str | None = None
    security_csp_report_endpoint_enabled: bool = False

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_trust_x_forwarded_for: bool = False
    rate_limit_trusted_proxy_cidrs: str = ""
    rate_limit_global_requests: int = 240
    rate_limit_global_window_seconds: int = 60
    rate_limit_global_authenticated_requests: int = 1200
    rate_limit_global_authenticated_window_seconds: int = 60
    rate_limit_auth_requests: int = 20
    rate_limit_auth_window_seconds: int = 60
    rate_limit_auth_login_requests: int = 8
    rate_limit_auth_login_window_seconds: int = 60
    rate_limit_password_reset_requests: int = 5
    rate_limit_password_reset_window_seconds: int = 300
    rate_limit_agro_general_requests: int = 40
    rate_limit_agro_general_window_seconds: int = 60
    rate_limit_agro_ai_requests: int = 10
    rate_limit_agro_ai_window_seconds: int = 60
    rate_limit_storage: str = "memory"  # memory | redis
    rate_limit_redis_url: str | None = None
    rate_limit_redis_prefix: str = "wr:ratelimit"
    rate_limit_redis_connect_timeout_seconds: float = 1.0
    rate_limit_redis_socket_timeout_seconds: float = 1.0
    rate_limit_redis_required: bool = False

    # Metrics/observability
    metrics_enabled: bool = False
    metrics_require_prometheus_client: bool = False
    metrics_path: str = "/metrics"
    metrics_bearer_token: str | None = None
    workers_list_cache_enabled: bool = True
    workers_list_cache_ttl_seconds: int = 20
    workers_list_cache_max_entries: int = 500

    # Audit alerting
    audit_alert_enabled: bool = True
    audit_alert_window_seconds: int = 300
    audit_alert_auth_login_failed_threshold: int = 20
    audit_alert_password_reset_failed_threshold: int = 10
    audit_alert_agro_abuse_threshold: int = 30

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
