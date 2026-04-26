from sqlalchemy import select

from app.core.mfa_totp import totp_now
from app.db.session import SessionLocal
from app.models.user import User
from tests.helpers import _clear_tables, client


def _register(phone: str) -> None:
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Mfa User",
            "phone": phone,
            "email": "mfa.user@example.com",
            "role": "farmer",
            "password": "secret123",
            "terms_accepted": True,
            "data_consent_accepted": True,
            "consent_version": "2026-04-13",
        },
    )
    assert response.status_code == 201


def _login(phone: str, otp_code: str | None = None):
    payload = {"phone": phone, "password": "secret123", "legal_acknowledged": True}
    if otp_code is not None:
        payload["otp_code"] = otp_code
    return client.post("/auth/login", json=payload)


def test_mfa_setup_enable_and_login_flow() -> None:
    _clear_tables()
    phone = "+2127998111"
    _register(phone)

    login = _login(phone)
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    setup = client.post("/auth/mfa/setup", json={"current_password": "secret123"}, headers=headers)
    assert setup.status_code == 200
    setup_payload = setup.json()
    assert setup_payload["secret"]
    assert setup_payload["otpauth_uri"].startswith("otpauth://totp/")

    wrong_enable = client.post("/auth/mfa/enable", json={"otp_code": "000000"}, headers=headers)
    assert wrong_enable.status_code == 400

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.phone == phone))
        assert user is not None
        pending_secret = str(user.mfa_totp_pending_secret or "")
    assert pending_secret

    code = totp_now(pending_secret)
    enable = client.post("/auth/mfa/enable", json={"otp_code": code}, headers=headers)
    assert enable.status_code == 200

    login_without_otp = _login(phone)
    assert login_without_otp.status_code == 401
    detail = login_without_otp.json().get("detail", {})
    assert isinstance(detail, dict)
    assert detail.get("code") == "mfa_required"

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.phone == phone))
        assert user is not None
        active_secret = str(user.mfa_totp_secret or "")
        assert user.mfa_enabled is True
    assert active_secret

    login_with_otp = _login(phone, otp_code=totp_now(active_secret))
    assert login_with_otp.status_code == 200
    assert login_with_otp.json()["user"]["mfa_enabled"] is True


def test_mfa_disable_requires_password_and_otp() -> None:
    _clear_tables()
    phone = "+2127998112"
    _register(phone)
    login = _login(phone)
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    setup = client.post("/auth/mfa/setup", json={"current_password": "secret123"}, headers=headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    enable = client.post("/auth/mfa/enable", json={"otp_code": totp_now(secret)}, headers=headers)
    assert enable.status_code == 200

    login_with_otp = _login(phone, otp_code=totp_now(secret))
    assert login_with_otp.status_code == 200
    headers = {"Authorization": f"Bearer {login_with_otp.json()['access_token']}"}

    bad_disable = client.post(
        "/auth/mfa/disable",
        json={"current_password": "secret123", "otp_code": "000000"},
        headers=headers,
    )
    assert bad_disable.status_code == 400

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.phone == phone))
        assert user is not None
        active_secret = str(user.mfa_totp_secret or "")
    disable = client.post(
        "/auth/mfa/disable",
        json={"current_password": "secret123", "otp_code": totp_now(active_secret)},
        headers=headers,
    )
    assert disable.status_code == 200

    login_without_otp = _login(phone)
    assert login_without_otp.status_code == 200
    assert login_without_otp.json()["user"]["mfa_enabled"] is False
