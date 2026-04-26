from __future__ import annotations

import logging
import math
import time
import uuid
from ipaddress import ip_address, ip_network
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Iterable, Literal, Protocol

from fastapi import Request
from jose import JWTError, jwt
from starlette.responses import JSONResponse, Response

from app.core.audit import AGRO_RATE_LIMIT_BLOCK, emit_audit
from app.core.config import settings
from app.core.observability import (
    log_security_event,
    observe_rate_limit_backend_error,
    observe_rate_limit_block,
)

try:
    import redis.asyncio as redis_async
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover
    redis_async = None

    class RedisError(Exception):
        pass


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int
    path_prefixes: tuple[str, ...]
    methods: frozenset[str] | None = None


class RateLimitBackend(Protocol):
    async def check(self, rule: RateLimitRule, key: str) -> tuple[bool, int]: ...

    async def reset(self) -> None: ...

    async def healthcheck(self) -> tuple[bool, str]: ...


class InMemoryRateLimitBackend:
    """
    Sliding-window rate limiter in process memory.

    This is safe as fallback but does not coordinate across multiple app instances.
    """

    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()
        self._last_cleanup = time.monotonic()

    def _periodic_cleanup(self, now: float, max_window_seconds: int) -> None:
        if (now - self._last_cleanup) < 60:
            return
        stale_cutoff = now - max_window_seconds
        keys_to_delete: list[tuple[str, str]] = []
        for compound_key, timestamps in self._events.items():
            while timestamps and timestamps[0] <= stale_cutoff:
                timestamps.popleft()
            if not timestamps:
                keys_to_delete.append(compound_key)
        for compound_key in keys_to_delete:
            self._events.pop(compound_key, None)
        self._last_cleanup = now

    async def check(self, rule: RateLimitRule, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        compound_key = (rule.name, key)
        with self._lock:
            self._periodic_cleanup(now=now, max_window_seconds=rule.window_seconds)
            timestamps = self._events.setdefault(compound_key, deque())
            cutoff = now - rule.window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= rule.limit:
                retry_after = max(1, int(math.ceil(rule.window_seconds - (now - timestamps[0]))))
                return False, retry_after

            timestamps.append(now)
            return True, 0

    async def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._last_cleanup = time.monotonic()

    async def healthcheck(self) -> tuple[bool, str]:
        return True, "ok"


class RedisRateLimitBackend:
    """
    Sliding-window limiter backed by Redis sorted sets with atomic Lua script.
    """

    LUA_CHECK_AND_ADD = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local ttl_seconds = tonumber(ARGV[5])

local cutoff = now_ms - window_ms
redis.call("ZREMRANGEBYSCORE", key, "-inf", cutoff)
local count = redis.call("ZCARD", key)

if count >= limit then
  local first = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
  local first_ms = tonumber(first[2]) or now_ms
  local retry_ms = window_ms - (now_ms - first_ms)
  if retry_ms < 1 then retry_ms = 1 end
  return {0, retry_ms}
end

redis.call("ZADD", key, now_ms, member)
redis.call("EXPIRE", key, ttl_seconds)
return {1, 0}
"""

    def __init__(self) -> None:
        if redis_async is None:
            raise RuntimeError("Redis package is not installed but redis rate limiting was requested.")

        redis_url = str(settings.rate_limit_redis_url or "").strip()
        if not redis_url:
            raise RuntimeError("RATE_LIMIT_REDIS_URL is required when RATE_LIMIT_STORAGE=redis.")

        self._prefix = str(settings.rate_limit_redis_prefix or "wr:ratelimit").strip() or "wr:ratelimit"
        self._client = redis_async.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=float(settings.rate_limit_redis_connect_timeout_seconds),
            socket_timeout=float(settings.rate_limit_redis_socket_timeout_seconds),
        )
        self._sha: str | None = None

    async def _ensure_script(self) -> str:
        if self._sha is not None:
            return self._sha
        self._sha = await self._client.script_load(self.LUA_CHECK_AND_ADD)
        return self._sha

    def _redis_key(self, rule_name: str, identity_key: str) -> str:
        return f"{self._prefix}:{rule_name}:{identity_key}"

    async def check(self, rule: RateLimitRule, key: str) -> tuple[bool, int]:
        now_ms = int(time.time() * 1000)
        window_ms = int(max(1, rule.window_seconds) * 1000)
        limit = int(max(1, rule.limit))
        member = f"{now_ms}-{uuid.uuid4().hex}"
        ttl_seconds = int(max(2, rule.window_seconds + 2))
        redis_key = self._redis_key(rule.name, key)

        sha = await self._ensure_script()
        try:
            raw = await self._client.evalsha(
                sha,
                1,
                redis_key,
                now_ms,
                window_ms,
                limit,
                member,
                ttl_seconds,
            )
        except RedisError:
            # Script could be evicted; retry once with reload.
            self._sha = None
            sha = await self._ensure_script()
            raw = await self._client.evalsha(
                sha,
                1,
                redis_key,
                now_ms,
                window_ms,
                limit,
                member,
                ttl_seconds,
            )

        allowed = int(raw[0]) == 1
        retry_after_ms = int(raw[1]) if len(raw) > 1 else 0
        retry_after = max(1, int(math.ceil(retry_after_ms / 1000))) if not allowed else 0
        return allowed, retry_after

    async def reset(self) -> None:
        # Test helper only. Deletes keys in the configured prefix.
        cursor: int | str | bytes = 0
        pattern = f"{self._prefix}:*"
        while True:
            cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=1000)
            if keys:
                await self._client.delete(*keys)
            if cursor in (0, "0", b"0"):
                break

    async def healthcheck(self) -> tuple[bool, str]:
        pong = await self._client.ping()
        if pong:
            return True, "ok"
        return False, "redis_ping_failed"


_memory_backend = InMemoryRateLimitBackend()
_redis_backend: RedisRateLimitBackend | None = None
_last_storage_mode: Literal["memory", "redis"] | None = None
_trusted_proxy_networks_cache: tuple[str, tuple] = ("", tuple())


def _coerce_positive_int(value: int, fallback: int) -> int:
    return value if isinstance(value, int) and value > 0 else fallback


def _trusted_proxy_networks() -> tuple:
    global _trusted_proxy_networks_cache
    raw = str(settings.rate_limit_trusted_proxy_cidrs or "").strip()
    cached_raw, cached_networks = _trusted_proxy_networks_cache
    if raw == cached_raw:
        return cached_networks

    networks = []
    for chunk in raw.split(","):
        cidr = chunk.strip()
        if not cidr:
            continue
        try:
            networks.append(ip_network(cidr, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid RATE_LIMIT_TRUSTED_PROXY_CIDRS entry: %s", cidr)
    _trusted_proxy_networks_cache = (raw, tuple(networks))
    return _trusted_proxy_networks_cache[1]


def _is_trusted_proxy_ip(value: str | None) -> bool:
    if not value:
        return False
    networks = _trusted_proxy_networks()
    if not networks:
        return False
    try:
        addr = ip_address(value)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def build_rate_limit_rules() -> list[RateLimitRule]:
    return [
        RateLimitRule(
            name="global",
            limit=_coerce_positive_int(settings.rate_limit_global_requests, 240),
            window_seconds=_coerce_positive_int(settings.rate_limit_global_window_seconds, 60),
            path_prefixes=("/",),
        ),
        RateLimitRule(
            name="auth_general",
            limit=_coerce_positive_int(settings.rate_limit_auth_requests, 20),
            window_seconds=_coerce_positive_int(settings.rate_limit_auth_window_seconds, 60),
            path_prefixes=("/auth/",),
        ),
        RateLimitRule(
            name="auth_login",
            limit=_coerce_positive_int(settings.rate_limit_auth_login_requests, 8),
            window_seconds=_coerce_positive_int(settings.rate_limit_auth_login_window_seconds, 60),
            path_prefixes=("/auth/login",),
            methods=frozenset({"POST"}),
        ),
        RateLimitRule(
            name="auth_password_reset",
            limit=_coerce_positive_int(settings.rate_limit_password_reset_requests, 5),
            window_seconds=_coerce_positive_int(settings.rate_limit_password_reset_window_seconds, 300),
            path_prefixes=("/auth/password-reset/request", "/auth/password-reset/confirm"),
            methods=frozenset({"POST"}),
        ),
        RateLimitRule(
            name="agro_general",
            limit=_coerce_positive_int(settings.rate_limit_agro_general_requests, 40),
            window_seconds=_coerce_positive_int(settings.rate_limit_agro_general_window_seconds, 60),
            path_prefixes=("/agro-copilot/",),
        ),
        RateLimitRule(
            name="agro_ai_calls",
            limit=_coerce_positive_int(settings.rate_limit_agro_ai_requests, 10),
            window_seconds=_coerce_positive_int(settings.rate_limit_agro_ai_window_seconds, 60),
            path_prefixes=("/agro-copilot/chat", "/agro-copilot/diagnose"),
            methods=frozenset({"POST"}),
        ),
    ]


def _matches_rule(path: str, method: str, rule: RateLimitRule) -> bool:
    if rule.methods is not None and method.upper() not in rule.methods:
        return False
    return any(path.startswith(prefix) for prefix in rule.path_prefixes)


def iter_matching_rules(path: str, method: str, rules: Iterable[RateLimitRule]) -> Iterable[RateLimitRule]:
    for rule in rules:
        if _matches_rule(path=path, method=method, rule=rule):
            yield rule


def _client_ip(request: Request) -> str:
    if settings.rate_limit_trust_x_forwarded_for:
        peer_ip = request.client.host if request.client and request.client.host else None
        if _is_trusted_proxy_ip(peer_ip):
            header_value = str(request.headers.get("x-forwarded-for", "")).strip()
            if header_value:
                first = header_value.split(",")[0].strip()
                if first:
                    return first
        elif request.headers.get("x-forwarded-for"):
            log_security_event(
                logger,
                "untrusted_forwarded_for_ignored",
                peer_ip=peer_ip,
                path=request.url.path,
            )
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _auth_subject(request: Request) -> str | None:
    auth_header = str(request.headers.get("authorization", "")).strip()
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.auth_secret_key, algorithms=[settings.auth_algorithm])
    except JWTError:
        return None
    subject = str(payload.get("sub", "")).strip()
    return subject or None


def identity_key(request: Request) -> str:
    subject = _auth_subject(request)
    if subject:
        return f"user:{subject}"
    return f"ip:{_client_ip(request)}"


def _configured_storage_mode() -> Literal["memory", "redis"]:
    raw = str(settings.rate_limit_storage or "memory").strip().lower()
    return "redis" if raw == "redis" else "memory"


async def _active_backend() -> RateLimitBackend:
    global _redis_backend, _last_storage_mode

    mode = _configured_storage_mode()
    if mode != _last_storage_mode:
        _last_storage_mode = mode

    if mode == "memory":
        return _memory_backend

    if _redis_backend is None:
        try:
            _redis_backend = RedisRateLimitBackend()
        except Exception as exc:
            if settings.rate_limit_redis_required:
                raise
            logger.warning("Redis rate limiter unavailable; falling back to memory backend: %s", exc)
            observe_rate_limit_backend_error(mode="redis", phase="init")
            return _memory_backend

    return _redis_backend


async def reset_rate_limiter_state() -> None:
    global _redis_backend, _last_storage_mode
    await _memory_backend.reset()
    if _redis_backend is not None:
        try:
            await _redis_backend.reset()
        except Exception:
            pass
    _redis_backend = None
    _last_storage_mode = None


async def rate_limiter_healthcheck() -> tuple[bool, dict[str, str]]:
    mode = _configured_storage_mode()
    if not settings.rate_limit_enabled:
        return True, {"mode": mode, "status": "disabled"}
    try:
        backend = await _active_backend()
        ok, reason = await backend.healthcheck()
        if ok:
            return True, {"mode": mode, "status": "ok"}
        return False, {"mode": mode, "status": reason}
    except Exception as exc:
        return False, {"mode": mode, "status": f"error:{exc.__class__.__name__}"}


def _rate_limit_block_response(rule_name: str, retry_after_seconds: int) -> Response:
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "rule": rule_name,
            "retry_after_seconds": retry_after_seconds,
        },
        headers={"Retry-After": str(retry_after_seconds)},
    )


async def enforce_rate_limit(request: Request, rules: list[RateLimitRule]) -> Response | None:
    if not settings.rate_limit_enabled:
        return None
    if request.url.path == "/health":
        return None

    try:
        backend = await _active_backend()
    except Exception:
        if settings.rate_limit_redis_required:
            logger.exception("Rate limiter backend unavailable in strict mode.")
            observe_rate_limit_backend_error(mode="redis", phase="init_strict")
            return JSONResponse(status_code=503, content={"detail": "Rate limiter backend unavailable"})
        logger.warning("Rate limiter backend unavailable, failing open for availability.")
        observe_rate_limit_backend_error(mode="redis", phase="init_fail_open")
        return None
    key = identity_key(request)

    for rule in iter_matching_rules(path=request.url.path, method=request.method, rules=rules):
        try:
            allowed, retry_after = await backend.check(rule=rule, key=key)
        except Exception as exc:
            if settings.rate_limit_redis_required:
                logger.exception("Rate limiter backend failed in strict mode.")
                observe_rate_limit_backend_error(mode=_configured_storage_mode(), phase="check_strict")
                return JSONResponse(status_code=503, content={"detail": "Rate limiter backend unavailable"})
            logger.warning("Rate limiter backend error, failing open for availability: %s", exc)
            observe_rate_limit_backend_error(mode=_configured_storage_mode(), phase="check_fail_open")
            return None

        if allowed:
            continue
        observe_rate_limit_block(rule=rule.name, method=request.method, path=request.url.path)
        log_security_event(
            logger,
            "rate_limit_blocked",
            rule=rule.name,
            method=request.method.upper(),
            path=request.url.path,
            identity=key,
            retry_after_seconds=retry_after,
        )
        if rule.name.startswith("agro"):
            emit_audit(
                AGRO_RATE_LIMIT_BLOCK,
                request=request,
                metadata={"rule": rule.name, "identity": key, "retry_after_seconds": retry_after},
            )
        return _rate_limit_block_response(rule_name=rule.name, retry_after_seconds=retry_after)

    return None
