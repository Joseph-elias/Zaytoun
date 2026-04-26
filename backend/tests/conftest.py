import os
from pathlib import Path
import asyncio

import pytest

_override_url = os.getenv("TEST_DATABASE_URL")
if _override_url:
    TEST_DB_URL = _override_url
    TEST_DB_PATH = None
else:
    _override_path = os.getenv("TEST_DB_PATH")
    if _override_path:
        TEST_DB_PATH = Path(_override_path).resolve()
    else:
        TEST_DB_PATH = Path(__file__).resolve().parent / "test_worker_radar.db"
    TEST_DB_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["DB_FALLBACK_URL"] = TEST_DB_URL
os.environ.setdefault("RATE_LIMIT_ENABLED", "true")
os.environ.setdefault("RATE_LIMIT_GLOBAL_REQUESTS", "100000")
os.environ.setdefault("RATE_LIMIT_AUTH_REQUESTS", "100000")
os.environ.setdefault("RATE_LIMIT_AUTH_LOGIN_REQUESTS", "100000")
os.environ.setdefault("RATE_LIMIT_PASSWORD_RESET_REQUESTS", "100000")
os.environ.setdefault("RATE_LIMIT_AGRO_GENERAL_REQUESTS", "100000")
os.environ.setdefault("RATE_LIMIT_AGRO_AI_REQUESTS", "100000")

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.core.rate_limit import reset_rate_limiter_state  # noqa: E402
from app.models.booking import Booking  # noqa: F401,E402
from app.models.booking_event import BookingEvent  # noqa: F401,E402
from app.models.booking_message import BookingMessage  # noqa: F401,E402
from app.models.user import User  # noqa: F401,E402
from app.models.worker import Worker  # noqa: F401,E402
from app.models.olive_season import FarmerOliveSeason  # noqa: F401,E402
from app.models.olive_piece_metric import FarmerOlivePieceMetric  # noqa: F401,E402
from app.models.olive_labor_day import FarmerOliveLaborDay  # noqa: F401,E402
from app.models.olive_sale import FarmerOliveSale  # noqa: F401,E402
from app.models.olive_usage import FarmerOliveUsage  # noqa: F401,E402
from app.models.olive_inventory_item import FarmerOliveInventoryItem  # noqa: F401,E402
from app.models.olive_land_piece import FarmerOliveLandPiece  # noqa: F401,E402
from app.models.market_item import FarmerMarketItem  # noqa: F401,E402
from app.models.market_order import MarketOrder  # noqa: F401,E402
from app.models.market_order_message import MarketOrderMessage  # noqa: F401,E402
from app.models.worker_availability_slot import WorkerAvailabilitySlot  # noqa: F401,E402


def pytest_sessionstart(session):
    if TEST_DB_PATH and TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=engine)


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    if TEST_DB_PATH and TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(autouse=True)
def _reset_rate_limiter_between_tests():
    asyncio.run(reset_rate_limiter_state())
    try:
        yield
    finally:
        asyncio.run(reset_rate_limiter_state())
