from __future__ import annotations

from app.core.config import settings


def parse_cors_origins() -> list[str]:
    raw = str(settings.cors_allowed_origins or "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _is_production() -> bool:
    return str(settings.app_env or "development").strip().lower() == "production"


def _is_default_auth_secret() -> bool:
    return str(settings.auth_secret_key or "").strip() in {"", "change-me-in-production"}


def validate_startup_settings_or_raise() -> None:
    if not settings.startup_fail_fast_validation:
        return

    env_name = str(settings.app_env or "development").strip().lower()
    if env_name not in {"development", "staging", "production"}:
        raise RuntimeError("APP_ENV must be one of: development, staging, production.")

    if not _is_production():
        return

    errors: list[str] = []
    cors_origins = parse_cors_origins()
    if not cors_origins:
        errors.append("CORS_ALLOWED_ORIGINS is empty in production.")
    if any(origin == "*" for origin in cors_origins):
        errors.append("CORS_ALLOWED_ORIGINS cannot include '*' in production.")

    if _is_default_auth_secret():
        errors.append("AUTH_SECRET_KEY is default/empty in production.")

    if not settings.rate_limit_enabled:
        errors.append("RATE_LIMIT_ENABLED=false is not allowed in production.")

    if str(settings.rate_limit_storage or "memory").strip().lower() == "redis":
        if not str(settings.rate_limit_redis_url or "").strip():
            errors.append("RATE_LIMIT_STORAGE=redis requires RATE_LIMIT_REDIS_URL in production.")
        if not settings.rate_limit_redis_required:
            errors.append("RATE_LIMIT_REDIS_REQUIRED should be true in production when using redis limiter.")

    if not str(settings.security_trusted_hosts or "").strip():
        errors.append("SECURITY_TRUSTED_HOSTS is empty in production.")

    if not settings.security_hsts_enabled:
        errors.append("SECURITY_HSTS_ENABLED should be true in production.")

    if settings.security_content_security_policy_report_only:
        report_uri = str(settings.security_content_security_policy_report_uri or "").strip()
        if not report_uri and not settings.security_csp_report_endpoint_enabled:
            errors.append(
                "CSP report-only is enabled in production but no report URI/endpoint is configured."
            )

    if errors:
        raise RuntimeError("Startup security validation failed: " + " | ".join(errors))
