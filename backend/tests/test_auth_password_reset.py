from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from tests.helpers import _clear_tables, client


def _register_user(phone: str, password: str = "secret123") -> None:
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Reset User",
            "phone": phone,
            "role": "farmer",
            "password": password,
            "terms_accepted": True,
            "data_consent_accepted": True,
            "consent_version": "2026-04-13",
        },
    )
    assert response.status_code == 201


def test_password_reset_request_is_generic_for_unknown_phone() -> None:
    _clear_tables()

    response = client.post("/auth/password-reset/request", json={"phone": "+2127991000"})
    assert response.status_code == 200
    assert response.json()["message"] == "If the account exists, a password reset code has been generated."
    assert response.json().get("debug_reset_code") is None


def test_password_reset_confirm_updates_password() -> None:
    _clear_tables()
    _register_user("+2127991001", "secret123")
    login_before = client.post(
        "/auth/login",
        json={"phone": "+2127991001", "password": "secret123", "legal_acknowledged": True},
    )
    assert login_before.status_code == 200
    old_headers = {"Authorization": f"Bearer {login_before.json()['access_token']}"}

    old_dev_mode = settings.auth_password_reset_dev_mode
    settings.auth_password_reset_dev_mode = True
    try:
        request = client.post("/auth/password-reset/request", json={"phone": "+2127991001"})
        assert request.status_code == 200
        reset_code = request.json().get("debug_reset_code")
        assert isinstance(reset_code, str) and len(reset_code) >= 6

        confirm = client.post(
            "/auth/password-reset/confirm",
            json={
                "phone": "+2127991001",
                "reset_code": reset_code,
                "new_password": "new-secret-123",
            },
        )
        assert confirm.status_code == 200
        assert confirm.json()["message"] == "Your password has been updated. You can now log in."
    finally:
        settings.auth_password_reset_dev_mode = old_dev_mode

    old_session_after_reset = client.get("/auth/me", headers=old_headers)
    assert old_session_after_reset.status_code == 401

    old_login = client.post(
        "/auth/login",
        json={"phone": "+2127991001", "password": "secret123", "legal_acknowledged": True},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"phone": "+2127991001", "password": "new-secret-123", "legal_acknowledged": True},
    )
    assert new_login.status_code == 200


def test_password_reset_rejects_after_max_invalid_attempts() -> None:
    _clear_tables()
    _register_user("+2127991002", "secret123")

    old_dev_mode = settings.auth_password_reset_dev_mode
    old_max_attempts = settings.auth_password_reset_max_attempts
    settings.auth_password_reset_dev_mode = True
    settings.auth_password_reset_max_attempts = 2
    try:
        request = client.post("/auth/password-reset/request", json={"phone": "+2127991002"})
        assert request.status_code == 200
        valid_code = request.json().get("debug_reset_code")
        assert valid_code

        wrong_1 = client.post(
            "/auth/password-reset/confirm",
            json={"phone": "+2127991002", "reset_code": "999999", "new_password": "new-secret-123"},
        )
        assert wrong_1.status_code == 400

        wrong_2 = client.post(
            "/auth/password-reset/confirm",
            json={"phone": "+2127991002", "reset_code": "888888", "new_password": "new-secret-123"},
        )
        assert wrong_2.status_code == 400

        locked = client.post(
            "/auth/password-reset/confirm",
            json={
                "phone": "+2127991002",
                "reset_code": valid_code,
                "new_password": "new-secret-123",
            },
        )
        assert locked.status_code == 400
    finally:
        settings.auth_password_reset_dev_mode = old_dev_mode
        settings.auth_password_reset_max_attempts = old_max_attempts

    with SessionLocal() as session:
        user = session.query(User).filter(User.phone == "+2127991002").first()
        assert user is not None
        assert user.password_reset_attempts == 2
