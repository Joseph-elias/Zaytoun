from tests.helpers import _clear_tables, _register_and_login, _worker_payload, client


def test_account_settings_profile_update_and_password_change() -> None:
    _clear_tables()

    original_phone = "+2127993001"
    new_phone = "+2127993999"
    headers = _register_and_login("worker", original_phone)

    create_worker = client.post("/workers", json=_worker_payload(original_phone, name="Settings Team"), headers=headers)
    assert create_worker.status_code == 201

    me_before = client.get("/auth/me", headers=headers)
    assert me_before.status_code == 200
    assert me_before.json()["phone"] == original_phone

    profile_update_missing_reauth = client.patch(
        "/auth/me/profile",
        json={
            "full_name": "Worker Updated",
            "phone": new_phone,
            "email": "worker.updated@example.com",
        },
        headers=headers,
    )
    assert profile_update_missing_reauth.status_code == 400

    profile_update = client.patch(
        "/auth/me/profile",
        json={
            "full_name": "Worker Updated",
            "phone": new_phone,
            "email": "worker.updated@example.com",
            "current_password": "secret123",
        },
        headers=headers,
    )
    assert profile_update.status_code == 200
    assert profile_update.json()["full_name"] == "Worker Updated"
    assert profile_update.json()["phone"] == new_phone
    assert profile_update.json()["email"] == "worker.updated@example.com"

    workers_after_phone_change = client.get("/workers", headers=headers)
    assert workers_after_phone_change.status_code == 200
    assert len(workers_after_phone_change.json()) == 1
    assert workers_after_phone_change.json()[0]["phone"] == new_phone

    wrong_current_password = client.patch(
        "/auth/me/password",
        json={"current_password": "wrong123", "new_password": "new-secret-123"},
        headers=headers,
    )
    assert wrong_current_password.status_code == 400

    change_password = client.patch(
        "/auth/me/password",
        json={"current_password": "secret123", "new_password": "new-secret-123"},
        headers=headers,
    )
    assert change_password.status_code == 200

    old_session_after_change = client.get("/auth/me", headers=headers)
    assert old_session_after_change.status_code == 401

    old_login = client.post(
        "/auth/login",
        json={"phone": new_phone, "password": "secret123", "legal_acknowledged": True},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"phone": new_phone, "password": "new-secret-123", "legal_acknowledged": True},
    )
    assert new_login.status_code == 200
