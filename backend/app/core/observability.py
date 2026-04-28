from __future__ import annotations

import json
import re
import time
from typing import Any

from app.core.config import settings

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
    PROMETHEUS_IMPORT_ERROR: str | None = None
except Exception:  # pragma: no cover
    import traceback

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    Counter = None
    Histogram = None
    Gauge = None
    generate_latest = None
    PROMETHEUS_IMPORT_ERROR = traceback.format_exc(limit=1)


_uuid_like_re = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
_long_hex_re = re.compile(r"\b[0-9a-fA-F]{24,64}\b")
_numeric_re = re.compile(r"(?<=/)\d+(?=/|$)")


def _normalize_path(path: str) -> str:
    value = _uuid_like_re.sub(":id", str(path or ""))
    value = _long_hex_re.sub(":id", value)
    value = _numeric_re.sub(":id", value)
    return value or "/"


if Counter is not None and Histogram is not None:
    HTTP_REQUESTS_TOTAL = Counter(
        "worker_radar_http_requests_total",
        "Total HTTP requests.",
        ["method", "path", "status_code"],
    )
    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        "worker_radar_http_request_duration_seconds",
        "HTTP request latency in seconds.",
        ["method", "path"],
    )
    RATE_LIMIT_BLOCK_TOTAL = Counter(
        "worker_radar_rate_limit_block_total",
        "Number of requests blocked by rate limits.",
        ["rule", "method", "path"],
    )
    RATE_LIMIT_BACKEND_ERROR_TOTAL = Counter(
        "worker_radar_rate_limit_backend_error_total",
        "Rate limiter backend errors by phase/mode.",
        ["mode", "phase"],
    )
    DB_POOL_SIZE = Gauge(
        "worker_radar_db_pool_size",
        "Configured SQLAlchemy DB pool size.",
    )
    DB_POOL_CHECKED_OUT = Gauge(
        "worker_radar_db_pool_checked_out_connections",
        "Current number of checked out DB connections.",
    )
    DB_POOL_OVERFLOW = Gauge(
        "worker_radar_db_pool_overflow_connections",
        "Current DB pool overflow connections.",
    )
else:  # pragma: no cover
    HTTP_REQUESTS_TOTAL = None
    HTTP_REQUEST_DURATION_SECONDS = None
    RATE_LIMIT_BLOCK_TOTAL = None
    RATE_LIMIT_BACKEND_ERROR_TOTAL = None
    DB_POOL_SIZE = None
    DB_POOL_CHECKED_OUT = None
    DB_POOL_OVERFLOW = None


def now_monotonic() -> float:
    return time.monotonic()


def observe_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    normalized_path = _normalize_path(path)
    if HTTP_REQUESTS_TOTAL is not None:
        HTTP_REQUESTS_TOTAL.labels(method=method.upper(), path=normalized_path, status_code=str(status_code)).inc()
    if HTTP_REQUEST_DURATION_SECONDS is not None:
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method.upper(), path=normalized_path).observe(max(0.0, duration_seconds))


def observe_rate_limit_block(rule: str, method: str, path: str) -> None:
    if RATE_LIMIT_BLOCK_TOTAL is None:
        return
    RATE_LIMIT_BLOCK_TOTAL.labels(rule=rule, method=method.upper(), path=_normalize_path(path)).inc()


def observe_rate_limit_backend_error(mode: str, phase: str) -> None:
    if RATE_LIMIT_BACKEND_ERROR_TOTAL is None:
        return
    RATE_LIMIT_BACKEND_ERROR_TOTAL.labels(mode=mode, phase=phase).inc()


def observe_db_pool_state(pool_size: int, checked_out: int, overflow: int) -> None:
    if DB_POOL_SIZE is None or DB_POOL_CHECKED_OUT is None or DB_POOL_OVERFLOW is None:
        return
    DB_POOL_SIZE.set(max(0, int(pool_size)))
    DB_POOL_CHECKED_OUT.set(max(0, int(checked_out)))
    DB_POOL_OVERFLOW.set(max(0, int(overflow)))


def log_security_event(logger, event: str, **fields: Any) -> None:
    payload = {"event": event, "ts": int(time.time()), **fields}
    logger.warning("security_event=%s", json.dumps(payload, ensure_ascii=True, sort_keys=True))


def metrics_payload() -> bytes:
    if generate_latest is None:
        return (
            b"# TYPE worker_radar_http_requests_total counter\n"
            b"worker_radar_http_requests_total 0\n"
            b"# TYPE worker_radar_http_request_duration_seconds histogram\n"
            b"# TYPE worker_radar_rate_limit_block_total counter\n"
            b"worker_radar_rate_limit_block_total 0\n"
            b"# TYPE worker_radar_rate_limit_backend_error_total counter\n"
            b"worker_radar_rate_limit_backend_error_total 0\n"
        )
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def metrics_endpoint_enabled() -> bool:
    return bool(settings.metrics_enabled)


def metrics_backend_status() -> tuple[bool, str]:
    if generate_latest is None:
        return False, PROMETHEUS_IMPORT_ERROR or "prometheus_client_unavailable"
    return True, "ok"
