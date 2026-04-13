import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).resolve().parent / "test_worker_radar.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["DB_FALLBACK_URL"] = TEST_DB_URL

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
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
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=engine)


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
