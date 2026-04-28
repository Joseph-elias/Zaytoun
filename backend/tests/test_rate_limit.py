import asyncio

from app.core.config import settings
from app.core.rate_limit import reset_rate_limiter_state
from tests.helpers import _clear_tables, _register_and_login, client


def _snapshot_rate_limit_settings() -> dict[str, int | bool]:
    return {
        "rate_limit_enabled": settings.rate_limit_enabled,
        "rate_limit_global_requests": settings.rate_limit_global_requests,
        "rate_limit_global_window_seconds": settings.rate_limit_global_window_seconds,
        "rate_limit_global_authenticated_requests": settings.rate_limit_global_authenticated_requests,
        "rate_limit_global_authenticated_window_seconds": settings.rate_limit_global_authenticated_window_seconds,
        "rate_limit_auth_login_requests": settings.rate_limit_auth_login_requests,
        "rate_limit_auth_login_window_seconds": settings.rate_limit_auth_login_window_seconds,
        "rate_limit_agro_ai_requests": settings.rate_limit_agro_ai_requests,
        "rate_limit_agro_ai_window_seconds": settings.rate_limit_agro_ai_window_seconds,
    }


def _restore_rate_limit_settings(snapshot: dict[str, int | bool]) -> None:
    settings.rate_limit_enabled = bool(snapshot["rate_limit_enabled"])
    settings.rate_limit_global_requests = int(snapshot["rate_limit_global_requests"])
    settings.rate_limit_global_window_seconds = int(snapshot["rate_limit_global_window_seconds"])
    settings.rate_limit_global_authenticated_requests = int(snapshot["rate_limit_global_authenticated_requests"])
    settings.rate_limit_global_authenticated_window_seconds = int(snapshot["rate_limit_global_authenticated_window_seconds"])
    settings.rate_limit_auth_login_requests = int(snapshot["rate_limit_auth_login_requests"])
    settings.rate_limit_auth_login_window_seconds = int(snapshot["rate_limit_auth_login_window_seconds"])
    settings.rate_limit_agro_ai_requests = int(snapshot["rate_limit_agro_ai_requests"])
    settings.rate_limit_agro_ai_window_seconds = int(snapshot["rate_limit_agro_ai_window_seconds"])


def test_rate_limit_blocks_repeated_login_attempts() -> None:
    _clear_tables()
    asyncio.run(reset_rate_limiter_state())
    snapshot = _snapshot_rate_limit_settings()
    try:
        settings.rate_limit_enabled = True
        settings.rate_limit_global_requests = 500
        settings.rate_limit_global_window_seconds = 60
        settings.rate_limit_auth_login_requests = 2
        settings.rate_limit_auth_login_window_seconds = 60

        register_payload = {
            "full_name": "Farmer User",
            "phone": "+2127000101",
            "email": "farmer.2127000101@example.com",
            "role": "farmer",
            "password": "secret123",
            "terms_accepted": True,
            "data_consent_accepted": True,
            "consent_version": "2026-04-13",
        }
        register_response = client.post("/auth/register", json=register_payload)
        assert register_response.status_code == 201

        login_payload = {
            "phone": "+2127000101",
            "password": "secret123",
            "legal_acknowledged": True,
        }
        first = client.post("/auth/login", json=login_payload)
        second = client.post("/auth/login", json=login_payload)
        third = client.post("/auth/login", json=login_payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert "retry_after_seconds" in third.json()
    finally:
        _restore_rate_limit_settings(snapshot)
        asyncio.run(reset_rate_limiter_state())


def test_rate_limit_blocks_agro_ai_spam() -> None:
    _clear_tables()
    asyncio.run(reset_rate_limiter_state())
    snapshot = _snapshot_rate_limit_settings()
    try:
        settings.rate_limit_enabled = True
        settings.rate_limit_global_requests = 500
        settings.rate_limit_global_window_seconds = 60
        settings.rate_limit_agro_ai_requests = 2
        settings.rate_limit_agro_ai_window_seconds = 60

        farmer_headers = _register_and_login("farmer", "+2127000102")

        first = client.post("/agro-copilot/chat", json={"language": "en"}, headers=farmer_headers)
        second = client.post("/agro-copilot/chat", json={"language": "en"}, headers=farmer_headers)
        third = client.post("/agro-copilot/chat", json={"language": "en"}, headers=farmer_headers)

        assert first.status_code == 422
        assert second.status_code == 422
        assert third.status_code == 429
        assert third.json().get("rule") == "agro_ai_calls"
    finally:
        _restore_rate_limit_settings(snapshot)
        asyncio.run(reset_rate_limiter_state())


def test_global_ip_limit_does_not_block_authenticated_global_budget() -> None:
    _clear_tables()
    asyncio.run(reset_rate_limiter_state())
    snapshot = _snapshot_rate_limit_settings()
    try:
        settings.rate_limit_enabled = True
        settings.rate_limit_global_requests = 500
        settings.rate_limit_global_window_seconds = 60
        settings.rate_limit_global_authenticated_requests = 100
        settings.rate_limit_global_authenticated_window_seconds = 60
        settings.rate_limit_auth_login_requests = 50
        settings.rate_limit_auth_login_window_seconds = 60

        worker_headers = _register_and_login("worker", "+2127000199")
        settings.rate_limit_global_requests = 1
        asyncio.run(reset_rate_limiter_state())
        first_anon = client.get("/workers")
        second_anon = client.get("/workers")
        assert first_anon.status_code in (401, 403)
        assert second_anon.status_code == 429
        assert second_anon.json().get("rule") == "global_ip"

        authed = client.get("/workers", headers=worker_headers)
        assert authed.status_code == 200
    finally:
        _restore_rate_limit_settings(snapshot)
        asyncio.run(reset_rate_limiter_state())
