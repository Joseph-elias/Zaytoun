from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from app.models.worker import Worker

client = TestClient(app)


def _clear_tables() -> None:
    with SessionLocal() as session:
        session.query(Worker).delete()
        session.query(User).delete()
        session.commit()


def _register_and_login(role: str, phone: str) -> dict[str, str]:
    register_payload = {
        "full_name": f"{role.title()} User",
        "phone": phone,
        "role": role,
        "password": "secret123",
    }
    reg = client.post("/auth/register", json=register_payload)
    assert reg.status_code == 201

    login = client.post("/auth/login", json={"phone": phone, "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _worker_payload(phone: str, name: str = "Ali Ahmed") -> dict:
    return {
        "name": name,
        "phone": phone,
        "village": "Tiznit",
        "men_count": 2,
        "women_count": 1,
        "rate_type": "day",
        "men_rate_value": 150,
        "women_rate_value": 100,
        "overtime_open": True,
        "overtime_price": 20,
        "overtime_note": "Can work up to 2 extra hours.",
        "available": True,
    }


def test_auth_register_and_login() -> None:
    _clear_tables()

    payload = {
        "full_name": "Farmer One",
        "phone": "+2127000000",
        "role": "farmer",
        "password": "secret123",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201

    login = client.post("/auth/login", json={"phone": payload["phone"], "password": payload["password"]})
    assert login.status_code == 200
    assert "access_token" in login.json()
    assert login.json()["user"]["role"] == "farmer"


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
