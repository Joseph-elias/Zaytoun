from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any

from fastapi import Request

from app.core.config import settings


logger = logging.getLogger("app.audit")

_redact_keys = {"password", "new_password", "current_password", "reset_code", "token", "authorization", "api_key", "secret"}
_email_re = re.compile(r"([A-Za-z0-9._%+-]{2})[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def _mask_email(value: str | None) -> str | None:
    if not value:
        return value
    return _email_re.sub(r"\1***\2", value)


def _redact_value(key: str, value: Any) -> Any:
    if key.lower() in _redact_keys:
        return "***"
    if isinstance(value, str) and "@" in value:
        return _mask_email(value)
    return value


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, dict):
            clean[key] = {k: _redact_value(str(k), v) for k, v in value.items()}
        else:
            clean[key] = _redact_value(str(key), value)
    return clean


@dataclass(frozen=True)
class AuditEvent:
    event: str
    outcome: str
    category: str


AUTH_REGISTER = AuditEvent(event="auth.register", outcome="success", category="auth")
AUTH_REGISTER_FAILED = AuditEvent(event="auth.register", outcome="failure", category="auth")
AUTH_LOGIN = AuditEvent(event="auth.login", outcome="success", category="auth")
AUTH_LOGIN_FAILED = AuditEvent(event="auth.login", outcome="failure", category="auth")
AUTH_PROFILE_UPDATED = AuditEvent(event="auth.profile.update", outcome="success", category="auth")
AUTH_PASSWORD_CHANGED = AuditEvent(event="auth.password.change", outcome="success", category="auth")
AUTH_PASSWORD_RESET_REQUEST = AuditEvent(event="auth.password_reset.request", outcome="accepted", category="auth")
AUTH_PASSWORD_RESET_CONFIRM = AuditEvent(event="auth.password_reset.confirm", outcome="success", category="auth")
AUTH_PASSWORD_RESET_CONFIRM_FAILED = AuditEvent(event="auth.password_reset.confirm", outcome="failure", category="auth")
AUTH_CONSENT_REACCEPT = AuditEvent(event="auth.consent.reaccept", outcome="success", category="consent")
AUTH_ACCOUNT_DELETE = AuditEvent(event="auth.account.delete", outcome="success", category="auth")
AUTH_MFA_SETUP = AuditEvent(event="auth.mfa.setup", outcome="accepted", category="auth")
AUTH_MFA_SETUP_FAILED = AuditEvent(event="auth.mfa.setup", outcome="failure", category="auth")
AUTH_MFA_ENABLE = AuditEvent(event="auth.mfa.enable", outcome="success", category="auth")
AUTH_MFA_ENABLE_FAILED = AuditEvent(event="auth.mfa.enable", outcome="failure", category="auth")
AUTH_MFA_DISABLE = AuditEvent(event="auth.mfa.disable", outcome="success", category="auth")
AUTH_MFA_DISABLE_FAILED = AuditEvent(event="auth.mfa.disable", outcome="failure", category="auth")
AGRO_UPSTREAM_ERROR = AuditEvent(event="agro.upstream", outcome="failure", category="agro")
AGRO_RATE_LIMIT_BLOCK = AuditEvent(event="agro.abuse.rate_limit", outcome="blocked", category="abuse")

_alert_windows: dict[str, deque[int]] = {}
_alert_lock = Lock()


def _event_alert_threshold(event: AuditEvent) -> int:
    if event.event == "auth.login" and event.outcome == "failure":
        return int(settings.audit_alert_auth_login_failed_threshold)
    if event.event == "auth.password_reset.confirm" and event.outcome == "failure":
        return int(settings.audit_alert_password_reset_failed_threshold)
    if event.event == "agro.abuse.rate_limit":
        return int(settings.audit_alert_agro_abuse_threshold)
    return 0


def _record_alert_window_and_check(event: AuditEvent) -> tuple[bool, int, int]:
    threshold = _event_alert_threshold(event)
    if threshold <= 0 or not settings.audit_alert_enabled:
        return False, 0, threshold

    window_seconds = max(10, int(settings.audit_alert_window_seconds))
    now_ts = int(time.time())
    cutoff = now_ts - window_seconds
    key = f"{event.event}:{event.outcome}"

    with _alert_lock:
        window = _alert_windows.setdefault(key, deque())
        while window and window[0] < cutoff:
            window.popleft()
        window.append(now_ts)
        count = len(window)
    return count >= threshold, count, threshold


def request_context(request: Request | None) -> dict[str, Any]:
    if request is None:
        return {}
    request_id = getattr(getattr(request, "state", object()), "request_id", None)
    client_ip = request.client.host if request.client and request.client.host else None
    return {
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
        "client_ip": client_ip,
    }


def emit_audit(event: AuditEvent, request: Request | None = None, actor_user_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
    payload = {
        "id": uuid.uuid4().hex,
        "ts": int(time.time()),
        "event": event.event,
        "category": event.category,
        "outcome": event.outcome,
        "actor_user_id": actor_user_id,
        **request_context(request),
        "metadata": _safe_metadata(metadata),
    }
    logger.info("audit_event=%s", json.dumps(payload, ensure_ascii=True, sort_keys=True))

    should_alert, observed_count, threshold = _record_alert_window_and_check(event)
    if should_alert:
        alert_payload = {
            "event": event.event,
            "outcome": event.outcome,
            "window_seconds": max(10, int(settings.audit_alert_window_seconds)),
            "observed_count": observed_count,
            "threshold": threshold,
            "path": payload.get("path"),
            "method": payload.get("method"),
        }
        logger.warning("audit_alert=%s", json.dumps(alert_payload, ensure_ascii=True, sort_keys=True))
