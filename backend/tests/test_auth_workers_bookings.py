from tests.helpers import client, _clear_tables, _register_and_login, _create_land_piece, _worker_payload
from app.core.config import settings


def test_auth_register_and_login() -> None:
    _clear_tables()

    payload = {
        "full_name": "Farmer One",
        "phone": "+2127000000",
        "role": "farmer",
        "password": "secret123",
        "terms_accepted": True,
        "data_consent_accepted": True,
        "consent_version": "2026-04-13",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201

    login = client.post(
        "/auth/login",
        json={"phone": payload["phone"], "password": payload["password"], "legal_acknowledged": True},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()
    assert login.json()["user"]["role"] == "farmer"


def test_auth_requires_registration_and_login_consent_flags() -> None:
    _clear_tables()

    missing_consent = client.post(
        "/auth/register",
        json={
            "full_name": "Farmer Two",
            "phone": "+2127000999",
            "role": "farmer",
            "password": "secret123",
        },
    )
    assert missing_consent.status_code == 422

    ok_register = client.post(
        "/auth/register",
        json={
            "full_name": "Farmer Two",
            "phone": "+2127000999",
            "role": "farmer",
            "password": "secret123",
            "terms_accepted": True,
            "data_consent_accepted": True,
            "consent_version": "2026-04-13",
        },
    )
    assert ok_register.status_code == 201

    missing_login_ack = client.post(
        "/auth/login",
        json={"phone": "+2127000999", "password": "secret123"},
    )
    assert missing_login_ack.status_code == 422

    ok_login = client.post(
        "/auth/login",
        json={"phone": "+2127000999", "password": "secret123", "legal_acknowledged": True},
    )
    assert ok_login.status_code == 200


def test_consent_reaccept_flow_blocks_protected_endpoints_until_updated() -> None:
    _clear_tables()

    reg = client.post(
        "/auth/register",
        json={
            "full_name": "Farmer Consent",
            "phone": "+2127001888",
            "role": "farmer",
            "password": "secret123",
            "terms_accepted": True,
            "data_consent_accepted": True,
            "consent_version": "2026-04-13",
        },
    )
    assert reg.status_code == 201

    previous_version = settings.auth_consent_version
    settings.auth_consent_version = "2026-05-01"
    try:
        login = client.post(
            "/auth/login",
            json={"phone": "+2127001888", "password": "secret123", "legal_acknowledged": True},
        )
        assert login.status_code == 200
        assert login.json()["consent_reaccept_required"] is True
        assert login.json()["required_consent_version"] == "2026-05-01"
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        blocked = client.get("/workers", headers=headers)
        assert blocked.status_code == 403
        detail = blocked.json().get("detail", {})
        assert detail.get("code") == "consent_reaccept_required"

        wrong_version = client.patch(
            "/auth/consent",
            headers=headers,
            json={
                "legal_acknowledged": True,
                "terms_accepted": True,
                "data_consent_accepted": True,
                "consent_version": "2026-04-13",
            },
        )
        assert wrong_version.status_code == 400

        updated = client.patch(
            "/auth/consent",
            headers=headers,
            json={
                "legal_acknowledged": True,
                "terms_accepted": True,
                "data_consent_accepted": True,
                "consent_version": "2026-05-01",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["consent_version"] == "2026-05-01"

        allowed = client.get("/workers", headers=headers)
        assert allowed.status_code == 200
    finally:
        settings.auth_consent_version = previous_version

def test_worker_role_restrictions_and_ownership() -> None:
    _clear_tables()

    worker_a_phone = "+2127111111"
    worker_b_phone = "+2127222222"

    worker_a_headers = _register_and_login("worker", worker_a_phone)
    worker_b_headers = _register_and_login("worker", worker_b_phone)
    farmer_headers = _register_and_login("farmer", "+2127333333")

    # Worker A can create only with own phone
    own_payload = _worker_payload(worker_a_phone, name="Worker A Team")
    create_a = client.post("/workers", json=own_payload, headers=worker_a_headers)
    assert create_a.status_code == 201

    # Worker A cannot create under another worker phone
    wrong_phone_payload = _worker_payload(worker_b_phone, name="Illegal Team")
    create_wrong = client.post("/workers", json=wrong_phone_payload, headers=worker_a_headers)
    assert create_wrong.status_code == 403

    # Worker B creates own profile
    create_b = client.post("/workers", json=_worker_payload(worker_b_phone, name="Worker B Team"), headers=worker_b_headers)
    assert create_b.status_code == 201

    worker_a_id = create_a.json()["id"]
    worker_b_id = create_b.json()["id"]

    # Worker A sees only own profile
    list_a = client.get("/workers", headers=worker_a_headers)
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["phone"] == worker_a_phone

    # Worker B sees only own profile
    list_b = client.get("/workers", headers=worker_b_headers)
    assert list_b.status_code == 200
    assert len(list_b.json()) == 1
    assert list_b.json()[0]["phone"] == worker_b_phone

    # Farmer sees all profiles
    list_farmer = client.get("/workers", headers=farmer_headers)
    assert list_farmer.status_code == 200
    assert len(list_farmer.json()) == 2

    # Worker A cannot modify Worker B profile
    patch_other_worker = client.patch(
        f"/workers/{worker_b_id}/availability",
        json={"available": False},
        headers=worker_a_headers,
    )
    assert patch_other_worker.status_code == 404

    # Farmer cannot modify any worker profile
    patch_farmer = client.patch(
        f"/workers/{worker_a_id}/availability",
        json={"available": False},
        headers=farmer_headers,
    )
    assert patch_farmer.status_code == 403

    # Worker A can modify own profile
    patch_own = client.patch(
        f"/workers/{worker_a_id}/availability",
        json={"available": False},
        headers=worker_a_headers,
    )
    assert patch_own.status_code == 200
    assert patch_own.json()["available"] is False

def test_rate_filters_with_auth() -> None:
    _clear_tables()

    worker_phone = "+2127444444"
    worker_headers = _register_and_login("worker", worker_phone)
    farmer_headers = _register_and_login("farmer", "+2127555555")

    workers = [
        {
            "name": "Team A",
            "phone": worker_phone,
            "village": "Lille",
            "men_count": 1,
            "women_count": 1,
            "rate_type": "day",
            "men_rate_value": 150,
            "women_rate_value": 100,
            "overtime_open": False,
            "overtime_price": None,
            "overtime_note": None,
            "available_dates": ["2030-02-10", "2030-02-11"],
            "available": True,
        },
        {
            "name": "Team B",
            "phone": worker_phone,
            "village": "Lille",
            "men_count": 2,
            "women_count": 0,
            "rate_type": "hour",
            "men_rate_value": 18,
            "women_rate_value": None,
            "overtime_open": False,
            "overtime_price": None,
            "overtime_note": None,
            "available_dates": ["2030-02-10"],
            "available": True,
        },
        {
            "name": "Team C",
            "phone": worker_phone,
            "village": "Tiznit",
            "men_count": 0,
            "women_count": 2,
            "rate_type": "day",
            "men_rate_value": None,
            "women_rate_value": 90,
            "overtime_open": False,
            "overtime_price": None,
            "overtime_note": None,
            "available_dates": ["2030-02-12"],
            "available": True,
        },
    ]

    for payload in workers:
        response = client.post("/workers", json=payload, headers=worker_headers)
        assert response.status_code == 201

    by_rate_type = client.get("/workers?rate_type=day", headers=farmer_headers)
    assert by_rate_type.status_code == 200
    assert len(by_rate_type.json()) == 2

    by_men_range = client.get("/workers?min_men_rate=140&max_men_rate=160", headers=farmer_headers)
    assert by_men_range.status_code == 200
    assert len(by_men_range.json()) == 1
    assert by_men_range.json()[0]["name"] == "Team A"

    by_women_min = client.get("/workers?min_women_rate=95", headers=farmer_headers)
    assert by_women_min.status_code == 200
    assert len(by_women_min.json()) == 1
    assert by_women_min.json()[0]["name"] == "Team A"

def test_worker_can_delete_own_profile() -> None:
    _clear_tables()

    worker_phone = "+2127666666"
    worker_headers = _register_and_login("worker", worker_phone)
    other_worker_headers = _register_and_login("worker", "+2127777777")

    create = client.post("/workers", json=_worker_payload(worker_phone, name="Delete Me"), headers=worker_headers)
    assert create.status_code == 201
    worker_id = create.json()["id"]

    delete_unauthorized = client.delete(f"/workers/{worker_id}", headers=other_worker_headers)
    assert delete_unauthorized.status_code == 404

    delete_own = client.delete(f"/workers/{worker_id}", headers=worker_headers)
    assert delete_own.status_code == 204

    list_own = client.get("/workers", headers=worker_headers)
    assert list_own.status_code == 200
    assert len(list_own.json()) == 0

def test_non_confirmed_booking_can_be_updated_and_deleted_by_owners() -> None:
    _clear_tables()

    worker_phone = "+2127888888"
    worker_headers = _register_and_login("worker", worker_phone)
    farmer_headers = _register_and_login("farmer", "+2127999999")
    other_farmer_headers = _register_and_login("farmer", "+2127900000")

    create_worker = client.post("/workers", json=_worker_payload(worker_phone, name="Team Flex"), headers=worker_headers)
    assert create_worker.status_code == 201
    worker_id = create_worker.json()["id"]

    create_booking = client.post(
        f"/workers/{worker_id}/bookings",
        json={
            "requests": [{"work_date": "2030-01-02", "requested_men": 1, "requested_women": 1}],
            "note": "initial",
        },
        headers=farmer_headers,
    )
    assert create_booking.status_code == 201
    booking_id = create_booking.json()[0]["id"]

    farmer_update = client.patch(
        f"/bookings/{booking_id}/proposal",
        json={"requested_men": 2, "requested_women": 1, "note": "farmer update"},
        headers=farmer_headers,
    )
    assert farmer_update.status_code == 200
    assert farmer_update.json()["status"] == "pending_worker"
    assert farmer_update.json()["requested_men"] == 2

    worker_update = client.patch(
        f"/bookings/{booking_id}/proposal",
        json={"requested_men": 2, "requested_women": 1, "note": "worker update"},
        headers=worker_headers,
    )
    assert worker_update.status_code == 200
    assert worker_update.json()["status"] == "pending_farmer"
    assert worker_update.json()["requested_women"] == 1

    unauthorized_update = client.patch(
        f"/bookings/{booking_id}/proposal",
        json={"requested_men": 1, "requested_women": 1},
        headers=other_farmer_headers,
    )
    assert unauthorized_update.status_code == 404

    delete_booking = client.delete(f"/bookings/{booking_id}", headers=worker_headers)
    assert delete_booking.status_code == 204

    farmer_list = client.get("/bookings/mine", headers=farmer_headers)
    assert farmer_list.status_code == 200
    assert len(farmer_list.json()) == 0

def test_confirmed_booking_cannot_be_updated_or_deleted() -> None:
    _clear_tables()

    worker_phone = "+2127000011"
    worker_headers = _register_and_login("worker", worker_phone)
    farmer_headers = _register_and_login("farmer", "+2127000012")

    create_worker = client.post("/workers", json=_worker_payload(worker_phone, name="Team Locked"), headers=worker_headers)
    assert create_worker.status_code == 201
    worker_id = create_worker.json()["id"]

    create_booking = client.post(
        f"/workers/{worker_id}/bookings",
        json={
            "requests": [{"work_date": "2030-01-03", "requested_men": 1, "requested_women": 0}],
            "note": "initial",
        },
        headers=farmer_headers,
    )
    assert create_booking.status_code == 201
    booking_id = create_booking.json()[0]["id"]

    worker_accept = client.patch(
        f"/bookings/{booking_id}/worker-response",
        json={"action": "accept"},
        headers=worker_headers,
    )
    assert worker_accept.status_code == 200

    farmer_confirm = client.patch(
        f"/bookings/{booking_id}/farmer-validation",
        json={"action": "confirm"},
        headers=farmer_headers,
    )
    assert farmer_confirm.status_code == 200
    assert farmer_confirm.json()["status"] == "confirmed"

    update_confirmed = client.patch(
        f"/bookings/{booking_id}/proposal",
        json={"requested_men": 1, "requested_women": 1},
        headers=farmer_headers,
    )
    assert update_confirmed.status_code == 400

    delete_confirmed = client.delete(f"/bookings/{booking_id}", headers=worker_headers)
    assert delete_confirmed.status_code == 400

def test_worker_can_modify_own_profile() -> None:
    _clear_tables()

    worker_phone = "+2127001234"
    worker_headers = _register_and_login("worker", worker_phone)

    created = client.post("/workers", json=_worker_payload(worker_phone, name="Before Edit"), headers=worker_headers)
    assert created.status_code == 201
    worker_id = created.json()["id"]

    update_payload = {
        "name": "After Edit",
        "village": "Kfaraaka",
        "address": "Updated address",
        "latitude": None,
        "longitude": None,
        "men_count": 3,
        "women_count": 1,
        "rate_type": "day",
        "men_rate_value": 180,
        "women_rate_value": 110,
        "overtime_open": True,
        "overtime_price": 25,
        "overtime_note": "Updated note",
        "available_dates": ["2030-01-04", "2030-01-05"],
    }

    updated = client.patch(f"/workers/{worker_id}", json=update_payload, headers=worker_headers)
    assert updated.status_code == 200
    body = updated.json()
    assert body["name"] == "After Edit"
    assert body["men_count"] == 3
    assert body["women_count"] == 1

