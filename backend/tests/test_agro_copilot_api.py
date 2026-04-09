from app.core.config import settings
from tests.helpers import _clear_tables, _register_and_login, client


def test_agro_copilot_requires_farmer_role() -> None:
    _clear_tables()
    worker_headers = _register_and_login("worker", "+2127666611")

    response = client.get("/agro-copilot/health", headers=worker_headers)
    assert response.status_code == 403


def test_agro_copilot_reports_missing_service_config() -> None:
    _clear_tables()
    farmer_headers = _register_and_login("farmer", "+2127666612")

    previous_base_url = settings.agro_copilot_api_base_url
    settings.agro_copilot_api_base_url = None
    try:
        response = client.get("/agro-copilot/health", headers=farmer_headers)
    finally:
        settings.agro_copilot_api_base_url = previous_base_url

    assert response.status_code == 503
    assert "not configured" in str(response.json().get("detail", "")).lower()


def test_agro_copilot_chat_payload_validation() -> None:
    _clear_tables()
    farmer_headers = _register_and_login("farmer", "+2127666613")

    response = client.post("/agro-copilot/chat", json={"language": "en"}, headers=farmer_headers)
    assert response.status_code == 422
