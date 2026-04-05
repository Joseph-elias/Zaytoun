from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from app.models.worker import Worker
from app.models.olive_season import FarmerOliveSeason
from app.models.olive_piece_metric import FarmerOlivePieceMetric
from app.models.olive_labor_day import FarmerOliveLaborDay
from app.models.olive_sale import FarmerOliveSale
from app.models.olive_usage import FarmerOliveUsage
from app.models.olive_inventory_item import FarmerOliveInventoryItem
from app.models.olive_land_piece import FarmerOliveLandPiece

client = TestClient(app)


def _clear_tables() -> None:
    with SessionLocal() as session:
        session.query(FarmerOliveSale).delete()
        session.query(FarmerOliveInventoryItem).delete()
        session.query(FarmerOliveLandPiece).delete()
        session.query(FarmerOliveUsage).delete()
        session.query(FarmerOliveLaborDay).delete()
        session.query(FarmerOlivePieceMetric).delete()
        session.query(FarmerOliveSeason).delete()
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


def _create_land_piece(headers: dict[str, str], piece_name: str, season_year: int | None = None) -> None:
    payload = {"piece_name": piece_name}
    if season_year is not None:
        payload["season_year"] = season_year
    response = client.post("/olive-land-pieces", json=payload, headers=headers)
    assert response.status_code == 201

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
        "available_dates": ["2030-01-02", "2030-01-03"],
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

def test_farmer_olive_season_crud() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127012345")
    _create_land_piece(farmer_headers, "North Plot")
    _create_land_piece(farmer_headers, "South Plot")

    create = client.post(
        "/olive-seasons",
        json={
            "season_year": 2030,
            "land_pieces": 12,
            "land_piece_name": "North Plot",
            "estimated_chonbol": 1600,
            "actual_chonbol": 1400,
            "kg_per_land_piece": 116.67,
            "tanks_20l": 70,
            "notes": "good season",
        },
        headers=farmer_headers,
    )
    assert create.status_code == 201
    season_id = create.json()["id"]
    assert create.json()["kg_needed_per_tank"] == "1.67"

    create_second_piece_same_year = client.post(
        "/olive-seasons",
        json={
            "season_year": 2030,
            "land_pieces": 8,
            "land_piece_name": "South Plot",
            "estimated_chonbol": 800,
            "actual_chonbol": 720,
            "kg_per_land_piece": 90,
            "tanks_20l": 40,
            "notes": "second piece",
        },
        headers=farmer_headers,
    )
    assert create_second_piece_same_year.status_code == 201

    duplicate_same_piece = client.post(
        "/olive-seasons",
        json={
            "season_year": 2030,
            "land_pieces": 6,
            "land_piece_name": "North Plot",
            "estimated_chonbol": 700,
            "actual_chonbol": 640,
            "kg_per_land_piece": 80,
            "tanks_20l": 32,
            "notes": "duplicate",
        },
        headers=farmer_headers,
    )
    assert duplicate_same_piece.status_code == 400

    list_one = client.get("/olive-seasons/mine", headers=farmer_headers)
    assert list_one.status_code == 200
    assert len(list_one.json()) == 2

    update = client.patch(
        f"/olive-seasons/{season_id}",
        json={
            "season_year": 2030,
            "land_pieces": 12,
            "land_piece_name": "North Plot",
            "estimated_chonbol": 1700,
            "actual_chonbol": 1500,
            "kg_per_land_piece": 125,
            "tanks_20l": 75,
            "notes": "updated",
        },
        headers=farmer_headers,
    )
    assert update.status_code == 200
    assert update.json()["kg_needed_per_tank"] == "1.67"

    delete = client.delete(f"/olive-seasons/{season_id}", headers=farmer_headers)
    assert delete.status_code == 204

    list_after_delete = client.get("/olive-seasons/mine", headers=farmer_headers)
    assert list_after_delete.status_code == 200
    assert len(list_after_delete.json()) == 1




def test_farmer_olive_piece_metric_crud() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127012366")
    other_farmer_headers = _register_and_login("farmer", "+2127012367")

    create = client.post(
        "/olive-piece-metrics",
        json={
            "season_year": 2030,
            "piece_label": "Piece A",
            "harvested_kg": 500,
            "tanks_20l": 25,
            "notes": "first input",
        },
        headers=farmer_headers,
    )
    assert create.status_code == 201
    metric_id = create.json()["id"]
    assert create.json()["kg_needed_per_tank"] == "20.00"

    listed = client.get("/olive-piece-metrics/mine", headers=farmer_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    update = client.patch(
        f"/olive-piece-metrics/{metric_id}",
        json={
            "season_year": 2030,
            "piece_label": "Piece A",
            "harvested_kg": 480,
            "tanks_20l": 24,
            "notes": "updated",
        },
        headers=farmer_headers,
    )
    assert update.status_code == 200
    assert update.json()["kg_needed_per_tank"] == "20.00"

    forbidden_delete = client.delete(f"/olive-piece-metrics/{metric_id}", headers=other_farmer_headers)
    assert forbidden_delete.status_code == 404

    delete = client.delete(f"/olive-piece-metrics/{metric_id}", headers=farmer_headers)
    assert delete.status_code == 204

    listed_empty = client.get("/olive-piece-metrics/mine", headers=farmer_headers)
    assert listed_empty.status_code == 200
    assert len(listed_empty.json()) == 0




def test_farmer_olive_financial_layer() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127012450")
    _create_land_piece(farmer_headers, "East Plot")

    create_season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2031,
            "land_pieces": 10,
            "land_piece_name": "East Plot",
            "estimated_chonbol": 1200,
            "actual_chonbol": 1100,
            "kg_per_land_piece": 110,
            "tanks_20l": 60,
            "pressing_cost": 180,
            "notes": "finance test",
        },
        headers=farmer_headers,
    )
    assert create_season.status_code == 201
    season_id = create_season.json()["id"]

    labor_day_1 = client.post(
        "/olive-labor-days",
        json={
            "season_id": season_id,
            "work_date": "2031-10-01",
            "men_count": 4,
            "women_count": 2,
            "men_rate": 150,
            "women_rate": 120,
        },
        headers=farmer_headers,
    )
    assert labor_day_1.status_code == 201
    assert labor_day_1.json()["total_day_cost"] == "840.00"

    labor_day_2 = client.post(
        "/olive-labor-days",
        json={
            "season_id": season_id,
            "work_date": "2031-10-02",
            "men_count": 3,
            "women_count": 3,
            "men_rate": 150,
            "women_rate": 120,
        },
        headers=farmer_headers,
    )
    assert labor_day_2.status_code == 201

    sale_1 = client.post(
        "/olive-sales",
        json={
            "season_id": season_id,
            "sold_on": "2031-11-01",
            "tanks_sold": 20,
            "price_per_tank": 95,
            "buyer": "Local Mill",
        },
        headers=farmer_headers,
    )
    assert sale_1.status_code == 201
    assert sale_1.json()["total_revenue"] == "1900.00"

    raw_sale = client.post(
        "/olive-sales",
        json={
            "season_id": season_id,
            "sold_on": "2031-11-02",
            "sale_type": "raw_kg",
            "raw_kg_sold": 100,
            "price_per_kg": 2,
            "buyer": "Raw Buyer",
        },
        headers=farmer_headers,
    )
    assert raw_sale.status_code == 201
    assert raw_sale.json()["total_revenue"] == "200.00"
    assert raw_sale.json()["inventory_tanks_delta"] == "0.00"

    container_sale = client.post(
        "/olive-sales",
        json={
            "season_id": season_id,
            "sold_on": "2031-11-03",
            "sale_type": "processed_container",
            "containers_sold": 3,
            "container_size_label": "5L jar",
            "kg_per_container": 1.83,
            "price_per_container": 70,
            "buyer": "Retail Shop",
        },
        headers=farmer_headers,
    )
    assert container_sale.status_code == 201
    assert container_sale.json()["total_revenue"] == "210.00"
    assert container_sale.json()["inventory_tanks_delta"] == "3.00"
    custom_sale = client.post(
        "/olive-sales",
        json={
            "season_id": season_id,
            "sold_on": "2031-11-04",
            "sale_type": "custom_item",
            "custom_item_name": "Olive Soap",
            "custom_quantity_sold": 40,
            "custom_unit_label": "bar",
            "custom_price_per_unit": 3,
            "custom_inventory_tanks_delta": 1.5,
            "buyer": "Shop X",
        },
        headers=farmer_headers,
    )
    assert custom_sale.status_code == 201
    assert custom_sale.json()["total_revenue"] == "120.00"
    assert custom_sale.json()["inventory_tanks_delta"] == "1.50"
    season_rows = client.get("/olive-seasons/mine", headers=farmer_headers)
    assert season_rows.status_code == 200
    row = season_rows.json()[0]

    assert row["harvest_days"] == 2
    assert row["worker_days"] == 12
    assert row["labor_cost_total"] == "1650.00"
    assert row["pressing_cost"] == "180.00"
    assert row["total_cost"] == "1830.00"
    assert row["sold_tanks"] == "24.50"
    assert row["used_tanks"] == "0.00"
    assert row["sales_revenue_total"] == "2430.00"
    assert row["profit"] == "600.00"
    assert row["remaining_tanks"] == "35.50"

    add_usage = client.post(
        "/olive-usages",
        json={
            "season_id": season_id,
            "used_on": "2031-11-05",
            "tanks_used": 5,
            "usage_type": "home_use",
        },
        headers=farmer_headers,
    )
    assert add_usage.status_code == 201

    season_rows_after_usage = client.get("/olive-seasons/mine", headers=farmer_headers)
    assert season_rows_after_usage.status_code == 200
    row_after_usage = season_rows_after_usage.json()[0]
    assert row_after_usage["used_tanks"] == "5.00"
    assert row_after_usage["remaining_tanks"] == "30.50"

    labor_list = client.get(f"/olive-labor-days/mine?season_id={season_id}", headers=farmer_headers)
    assert labor_list.status_code == 200
    assert len(labor_list.json()) == 2

    sales_list = client.get(f"/olive-sales/mine?season_id={season_id}", headers=farmer_headers)
    assert sales_list.status_code == 200
    assert len(sales_list.json()) == 4







def test_farmer_inventory_page_flow_and_custom_sale_stock_deduction() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127012999")
    _create_land_piece(farmer_headers, "West Plot")

    create_season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2032,
            "land_pieces": 5,
            "land_piece_name": "West Plot",
            "estimated_chonbol": 900,
            "actual_chonbol": 850,
            "kg_per_land_piece": 850,
            "tanks_20l": 50,
            "pressing_cost": 100,
        },
        headers=farmer_headers,
    )
    assert create_season.status_code == 201
    season_id = create_season.json()["id"]

    create_item = client.post(
        "/olive-inventory-items",
        json={
            "item_name": "Olive Soap",
            "unit_label": "bar",
            "quantity_on_hand": 100,
            "default_price_per_unit": 3,
        },
        headers=farmer_headers,
    )
    assert create_item.status_code == 201
    item_id = create_item.json()["id"]

    sale = client.post(
        "/olive-sales",
        json={
            "season_id": season_id,
            "sold_on": "2032-11-01",
            "sale_type": "custom_item",
            "custom_inventory_item_id": item_id,
            "custom_quantity_sold": 15,
            "buyer": "Market A",
        },
        headers=farmer_headers,
    )
    assert sale.status_code == 201
    assert sale.json()["custom_item_name"] == "Olive Soap"
    assert sale.json()["custom_unit_label"] == "bar"
    assert sale.json()["custom_price_per_unit"] == "3.00"
    assert sale.json()["total_revenue"] == "45.00"

    inventory_rows = client.get("/olive-inventory-items/mine", headers=farmer_headers)
    assert inventory_rows.status_code == 200
    assert len(inventory_rows.json()) == 1
    assert inventory_rows.json()[0]["quantity_on_hand"] == "85.00"



def test_farmer_olive_land_pieces_registry() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127012777")

    create_one = client.post(
        "/olive-land-pieces",
        json={"piece_name": "North Plot"},
        headers=farmer_headers,
    )
    assert create_one.status_code == 201

    duplicate = client.post(
        "/olive-land-pieces",
        json={"piece_name": "  north   plot  "},
        headers=farmer_headers,
    )
    assert duplicate.status_code == 400

    rows = client.get("/olive-land-pieces/mine", headers=farmer_headers)
    assert rows.status_code == 200
    assert len(rows.json()) == 1

    create_season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2034,
            "land_pieces": 4,
            "land_piece_name": "North Plot",
            "estimated_chonbol": 500,
            "actual_chonbol": 480,
            "kg_per_land_piece": 480,
            "tanks_20l": 24,
        },
        headers=farmer_headers,
    )
    assert create_season.status_code == 201

    piece_id = create_one.json()["id"]
    delete_used = client.delete(f"/olive-land-pieces/{piece_id}", headers=farmer_headers)
    assert delete_used.status_code == 400

def test_farmer_olive_season_supports_pressing_cost_in_oil_tanks() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127013555")
    _create_land_piece(farmer_headers, "Mill Piece")

    create_season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2035,
            "land_pieces": 3,
            "land_piece_name": "Mill Piece",
            "estimated_chonbol": 300,
            "actual_chonbol": 280,
            "kg_per_land_piece": 280,
            "tanks_20l": 9,
            "tanks_taken_home_20l": 8,
            "pressing_cost_mode": "oil_tanks",
        },
        headers=farmer_headers,
    )
    assert create_season.status_code == 201
    row = create_season.json()
    assert row["pressing_cost_mode"] == "oil_tanks"
    assert row["pressing_cost"] == "1.00"
    assert row["pressing_cost_oil_tanks_20l"] == "1.00"
    assert row["tanks_taken_home_20l"] == "8.00"
    assert row["total_cost"] == "0.00"

    sale = client.post(
        "/olive-sales",
        json={
            "season_id": row["id"],
            "sold_on": "2035-11-10",
            "tanks_sold": 5,
            "price_per_tank": 100,
        },
        headers=farmer_headers,
    )
    assert sale.status_code == 201

    season_rows = client.get("/olive-seasons/mine", headers=farmer_headers)
    assert season_rows.status_code == 200
    updated = season_rows.json()[0]
    assert updated["remaining_tanks"] == "3.00"


def test_farmer_olive_season_rejects_taken_home_above_produced() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127013666")
    _create_land_piece(farmer_headers, "Validation Piece")

    create_season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2036,
            "land_pieces": 2,
            "land_piece_name": "Validation Piece",
            "estimated_chonbol": 200,
            "actual_chonbol": 190,
            "kg_per_land_piece": 190,
            "tanks_20l": 10,
            "tanks_taken_home_20l": 12,
            "pressing_cost_mode": "money",
            "pressing_cost": 50,
        },
        headers=farmer_headers,
    )
    assert create_season.status_code == 400


def test_farmer_olive_season_oil_mode_requires_produced_and_taken_home() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127013777")
    _create_land_piece(farmer_headers, "Missing Tanks Piece")

    create_season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2037,
            "land_pieces": 2,
            "land_piece_name": "Missing Tanks Piece",
            "pressing_cost_mode": "oil_tanks",
            "tanks_20l": 9,
        },
        headers=farmer_headers,
    )
    assert create_season.status_code == 400




def test_farmer_olive_season_rejects_unregistered_land_piece() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127013888")

    create_season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2038,
            "land_pieces": 2,
            "land_piece_name": "Unknown Piece",
            "tanks_20l": 10,
            "pressing_cost_mode": "money",
            "pressing_cost": 10,
        },
        headers=farmer_headers,
    )
    assert create_season.status_code == 400


def test_farmer_olive_season_rejects_land_piece_year_mismatch() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127013999")
    _create_land_piece(farmer_headers, "Year Locked Piece", 2025)

    create_season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2026,
            "land_pieces": 2,
            "land_piece_name": "Year Locked Piece",
            "tanks_20l": 10,
            "pressing_cost_mode": "money",
            "pressing_cost": 10,
        },
        headers=farmer_headers,
    )
    assert create_season.status_code == 400





def test_olive_season_uses_confirmed_bookings_for_harvest_days_and_labor_cost() -> None:
    _clear_tables()

    worker_phone = "+2127014001"
    worker_headers = _register_and_login("worker", worker_phone)
    farmer_headers = _register_and_login("farmer", "+2127014002")

    _create_land_piece(farmer_headers, "Booked Piece A")
    _create_land_piece(farmer_headers, "Booked Piece B")

    season_a = client.post(
        "/olive-seasons",
        json={
            "season_year": 2039,
            "land_pieces": 1,
            "land_piece_name": "Booked Piece A",
            "kg_per_land_piece": 100,
            "tanks_20l": 5,
            "pressing_cost": 10,
        },
        headers=farmer_headers,
    )
    assert season_a.status_code == 201

    season_b = client.post(
        "/olive-seasons",
        json={
            "season_year": 2039,
            "land_pieces": 1,
            "land_piece_name": "Booked Piece B",
            "kg_per_land_piece": 100,
            "tanks_20l": 5,
            "pressing_cost": 10,
        },
        headers=farmer_headers,
    )
    assert season_b.status_code == 201

    season_a_id = season_a.json()["id"]

    create_worker = client.post(
        "/workers",
        json={
            "name": "Booking Team",
            "phone": worker_phone,
            "village": "Lille",
            "men_count": 3,
            "women_count": 2,
            "rate_type": "day",
            "men_rate_value": 100,
            "women_rate_value": 80,
            "overtime_open": False,
            "overtime_price": None,
            "overtime_note": None,
            "available_dates": ["2039-10-01"],
            "available": True,
        },
        headers=worker_headers,
    )
    assert create_worker.status_code == 201
    worker_id = create_worker.json()["id"]

    booking = client.post(
        f"/workers/{worker_id}/bookings",
        json={
            "season_id": season_a_id,
            "requests": [{"work_date": "2039-10-01", "requested_men": 2, "requested_women": 1}],
            "note": "harvest booking",
        },
        headers=farmer_headers,
    )
    assert booking.status_code == 201
    assert booking.json()[0]["season_id"] == season_a_id
    booking_id = booking.json()[0]["id"]

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

    rows = client.get("/olive-seasons/mine", headers=farmer_headers)
    assert rows.status_code == 200

    by_piece = {row["land_piece_name"]: row for row in rows.json()}
    assert by_piece["Booked Piece A"]["harvest_days"] == 1
    assert by_piece["Booked Piece A"]["labor_cost_total"] == "280.00"
    assert by_piece["Booked Piece B"]["harvest_days"] == 0
    assert by_piece["Booked Piece B"]["labor_cost_total"] == "0.00"


def test_olive_season_keeps_booking_labor_when_old_season_link_becomes_orphan() -> None:
    _clear_tables()

    worker_phone = "+2127014011"
    worker_headers = _register_and_login("worker", worker_phone)
    farmer_headers = _register_and_login("farmer", "+2127014012")

    _create_land_piece(farmer_headers, "Orphan Link Piece")

    season_one = client.post(
        "/olive-seasons",
        json={
            "season_year": 2040,
            "land_pieces": 1,
            "land_piece_name": "Orphan Link Piece",
            "kg_per_land_piece": 100,
            "tanks_20l": 5,
            "pressing_cost": 10,
        },
        headers=farmer_headers,
    )
    assert season_one.status_code == 201
    season_one_id = season_one.json()["id"]

    create_worker = client.post(
        "/workers",
        json={
            "name": "Orphan Recovery Team",
            "phone": worker_phone,
            "village": "Lille",
            "men_count": 2,
            "women_count": 2,
            "rate_type": "day",
            "men_rate_value": 100,
            "women_rate_value": 80,
            "overtime_open": False,
            "overtime_price": None,
            "overtime_note": None,
            "available_dates": ["2040-10-01"],
            "available": True,
        },
        headers=worker_headers,
    )
    assert create_worker.status_code == 201
    worker_id = create_worker.json()["id"]

    booking = client.post(
        f"/workers/{worker_id}/bookings",
        json={
            "season_id": season_one_id,
            "requests": [{"work_date": "2040-10-01", "requested_men": 1, "requested_women": 1}],
            "note": "orphan season link test",
        },
        headers=farmer_headers,
    )
    assert booking.status_code == 201
    booking_id = booking.json()[0]["id"]

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

    delete_old_season = client.delete(f"/olive-seasons/{season_one_id}", headers=farmer_headers)
    assert delete_old_season.status_code == 204

    season_two = client.post(
        "/olive-seasons",
        json={
            "season_year": 2040,
            "land_pieces": 1,
            "land_piece_name": "Orphan Link Piece",
            "kg_per_land_piece": 100,
            "tanks_20l": 5,
            "pressing_cost": 10,
        },
        headers=farmer_headers,
    )
    assert season_two.status_code == 201

    rows = client.get("/olive-seasons/mine", headers=farmer_headers)
    assert rows.status_code == 200
    assert len(rows.json()) == 1
    row = rows.json()[0]
    assert row["land_piece_name"] == "Orphan Link Piece"
    assert row["harvest_days"] == 1
    assert row["labor_cost_total"] == "180.00"


def test_confirmed_booking_can_be_force_deleted_for_testing() -> None:
    _clear_tables()

    worker_phone = "+2127000013"
    worker_headers = _register_and_login("worker", worker_phone)
    farmer_headers = _register_and_login("farmer", "+2127000014")

    create_worker = client.post("/workers", json=_worker_payload(worker_phone, name="Team Force Delete"), headers=worker_headers)
    assert create_worker.status_code == 201
    worker_id = create_worker.json()["id"]

    create_booking = client.post(
        f"/workers/{worker_id}/bookings",
        json={
            "requests": [{"work_date": "2030-01-06", "requested_men": 1, "requested_women": 0}],
            "note": "force delete test",
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

    force_delete = client.delete(f"/bookings/{booking_id}?force=true", headers=farmer_headers)
    assert force_delete.status_code == 204

    farmer_list = client.get("/bookings/mine", headers=farmer_headers)
    assert farmer_list.status_code == 200
    assert len(farmer_list.json()) == 0


def test_olive_season_single_season_includes_unlinked_confirmed_bookings() -> None:
    _clear_tables()

    worker_phone = "+2127014021"
    worker_headers = _register_and_login("worker", worker_phone)
    farmer_headers = _register_and_login("farmer", "+2127014022")

    _create_land_piece(farmer_headers, "Single Piece")

    season = client.post(
        "/olive-seasons",
        json={
            "season_year": 2041,
            "land_pieces": 1,
            "land_piece_name": "Single Piece",
            "kg_per_land_piece": 100,
            "tanks_20l": 5,
            "pressing_cost": 10,
        },
        headers=farmer_headers,
    )
    assert season.status_code == 201

    create_worker = client.post(
        "/workers",
        json={
            "name": "Unlinked Booking Team",
            "phone": worker_phone,
            "village": "Lille",
            "men_count": 2,
            "women_count": 2,
            "rate_type": "day",
            "men_rate_value": 100,
            "women_rate_value": 80,
            "overtime_open": False,
            "overtime_price": None,
            "overtime_note": None,
            "available_dates": ["2041-10-05"],
            "available": True,
        },
        headers=worker_headers,
    )
    assert create_worker.status_code == 201
    worker_id = create_worker.json()["id"]

    booking = client.post(
        f"/workers/{worker_id}/bookings",
        json={
            "requests": [{"work_date": "2041-10-05", "requested_men": 1, "requested_women": 1}],
            "note": "no season id",
        },
        headers=farmer_headers,
    )
    assert booking.status_code == 201

    booking_id = booking.json()[0]["id"]
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

    rows = client.get("/olive-seasons/mine", headers=farmer_headers)
    assert rows.status_code == 200
    assert len(rows.json()) == 1
    row = rows.json()[0]
    assert row["harvest_days"] == 1
    assert row["labor_cost_total"] == "180.00"



def test_oil_tanks_pressing_cost_converts_to_money_when_tank_price_is_set() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127014031")
    _create_land_piece(farmer_headers, "Conversion Piece")

    created = client.post(
        "/olive-seasons",
        json={
            "season_year": 2042,
            "land_pieces": 1,
            "land_piece_name": "Conversion Piece",
            "kg_per_land_piece": 100,
            "tanks_20l": 9,
            "tanks_taken_home_20l": 8,
            "pressing_cost_mode": "oil_tanks",
        },
        headers=farmer_headers,
    )
    assert created.status_code == 201
    row = created.json()
    season_id = row["id"]
    assert row["pressing_cost_oil_tanks_20l"] == "1.00"
    assert row["total_cost"] == "0.00"

    updated = client.patch(
        f"/olive-seasons/{season_id}",
        json={
            "season_year": 2042,
            "land_pieces": 1,
            "land_piece_name": "Conversion Piece",
            "kg_per_land_piece": 100,
            "tanks_20l": 9,
            "tanks_taken_home_20l": 8,
            "pressing_cost_mode": "oil_tanks",
            "pressing_cost_oil_tank_unit_price": 50,
        },
        headers=farmer_headers,
    )
    assert updated.status_code == 200
    row2 = updated.json()
    assert row2["pressing_cost_oil_tank_unit_price"] == "50.00"
    assert row2["pressing_cost_money_equivalent"] == "50.00"
    assert row2["total_cost"] == "50.00"


def test_setting_oil_tank_price_does_not_overwrite_tank_pressing_values() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127014041")
    _create_land_piece(farmer_headers, "No Overwrite Piece")

    created = client.post(
        "/olive-seasons",
        json={
            "season_year": 2043,
            "land_pieces": 1,
            "land_piece_name": "No Overwrite Piece",
            "kg_per_land_piece": 100,
            "tanks_20l": 11,
            "tanks_taken_home_20l": 8,
            "pressing_cost_mode": "oil_tanks",
        },
        headers=farmer_headers,
    )
    assert created.status_code == 201
    season_id = created.json()["id"]

    updated_price = client.patch(
        f"/olive-seasons/{season_id}/oil-tank-price",
        json={"unit_price": 130},
        headers=farmer_headers,
    )
    assert updated_price.status_code == 200
    row = updated_price.json()
    assert row["pressing_cost_oil_tanks_20l"] == "3.00"
    assert row["pressing_cost_oil_tank_unit_price"] == "130.00"
    assert row["pressing_cost_money_equivalent"] == "390.00"
    assert row["total_cost"] == "390.00"

