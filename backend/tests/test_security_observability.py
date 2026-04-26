from starlette.requests import Request

from app.core import audit as audit_mod
from app.core.config import settings
from app.core.audit import AUTH_LOGIN_FAILED, emit_audit
from app.core.rate_limit import _client_ip
from app.main import app
from fastapi.testclient import TestClient


def _build_request(path: str, client_host: str, headers: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "query_string": b"",
        "headers": raw_headers,
        "client": (client_host, 50000),
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_forwarded_for_is_used_only_for_trusted_proxy() -> None:
    previous_trust = settings.rate_limit_trust_x_forwarded_for
    previous_cidrs = settings.rate_limit_trusted_proxy_cidrs
    settings.rate_limit_trust_x_forwarded_for = True
    settings.rate_limit_trusted_proxy_cidrs = "10.0.0.0/8"
    try:
        trusted = _build_request(
            path="/workers",
            client_host="10.2.3.4",
            headers={"x-forwarded-for": "203.0.113.10, 10.2.3.4"},
        )
        untrusted = _build_request(
            path="/workers",
            client_host="198.51.100.20",
            headers={"x-forwarded-for": "203.0.113.10"},
        )
        assert _client_ip(trusted) == "203.0.113.10"
        assert _client_ip(untrusted) == "198.51.100.20"
    finally:
        settings.rate_limit_trust_x_forwarded_for = previous_trust
        settings.rate_limit_trusted_proxy_cidrs = previous_cidrs


def test_metrics_endpoint_token_guard() -> None:
    previous_enabled = settings.metrics_enabled
    previous_token = settings.metrics_bearer_token
    settings.metrics_enabled = True
    settings.metrics_bearer_token = "metrics-secret"
    try:
        client = TestClient(app)
        no_auth = client.get("/metrics")
        wrong_auth = client.get("/metrics", headers={"Authorization": "Bearer wrong"})
        ok_auth = client.get("/metrics", headers={"Authorization": "Bearer metrics-secret"})

        assert no_auth.status_code == 401
        assert wrong_auth.status_code == 401
        assert ok_auth.status_code == 200
        assert b"worker_radar_http_requests_total" in ok_auth.content
    finally:
        settings.metrics_enabled = previous_enabled
        settings.metrics_bearer_token = previous_token


def test_request_id_header_is_propagated() -> None:
    client = TestClient(app)
    response = client.get("/health", headers={"X-Request-ID": "req-1234"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-1234"


def test_ready_endpoint_returns_structured_payload() -> None:
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "status" in body
    assert "ok" in body
    assert "checks" in body


def test_csp_report_endpoint_can_be_enabled() -> None:
    previous = settings.security_csp_report_endpoint_enabled
    settings.security_csp_report_endpoint_enabled = True
    try:
        client = TestClient(app)
        response = client.post("/csp-report", json={"csp-report": {"document-uri": "https://example.com"}})
        assert response.status_code == 204
    finally:
        settings.security_csp_report_endpoint_enabled = previous


def test_audit_burst_alert_is_emitted(caplog) -> None:
    prev_enabled = settings.audit_alert_enabled
    prev_window = settings.audit_alert_window_seconds
    prev_threshold = settings.audit_alert_auth_login_failed_threshold
    settings.audit_alert_enabled = True
    settings.audit_alert_window_seconds = 300
    settings.audit_alert_auth_login_failed_threshold = 2
    audit_mod._alert_windows.clear()
    try:
        caplog.clear()
        caplog.set_level("WARNING", logger="app.audit")
        emit_audit(AUTH_LOGIN_FAILED, metadata={"phone": "+2127000000"})
        emit_audit(AUTH_LOGIN_FAILED, metadata={"phone": "+2127000000"})
        assert any("audit_alert=" in message for message in caplog.messages)
    finally:
        settings.audit_alert_enabled = prev_enabled
        settings.audit_alert_window_seconds = prev_window
        settings.audit_alert_auth_login_failed_threshold = prev_threshold
        audit_mod._alert_windows.clear()
