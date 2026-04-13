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
from app.models.market_item import FarmerMarketItem
from app.models.market_order import MarketOrder
from app.models.market_order_message import MarketOrderMessage

client = TestClient(app)
def _clear_tables() -> None:
    with SessionLocal() as session:
        session.query(MarketOrderMessage).delete()
        session.query(MarketOrder).delete()
        session.query(FarmerMarketItem).delete()
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
    digits = "".join(ch for ch in phone if ch.isdigit()) or "user"
    register_payload = {
        "full_name": f"{role.title()} User",
        "phone": phone,
        "email": f"{role}.{digits}@example.com",
        "role": role,
        "password": "secret123",
        "terms_accepted": True,
        "data_consent_accepted": True,
        "consent_version": "2026-04-13",
    }
    reg = client.post("/auth/register", json=register_payload)
    assert reg.status_code == 201

    login = client.post(
        "/auth/login",
        json={"phone": phone, "password": "secret123", "legal_acknowledged": True},
    )
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
