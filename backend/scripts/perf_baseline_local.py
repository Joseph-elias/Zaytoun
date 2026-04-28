import os
import statistics
import time
from pathlib import Path

from fastapi.testclient import TestClient


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    idx = int(round((p / 100.0) * (len(values) - 1)))
    return sorted(values)[idx]


def run_case(client: TestClient, name: str, method: str, path: str, count: int = 200) -> dict:
    latencies = []
    status_counts: dict[int, int] = {}

    for _ in range(count):
        start = time.perf_counter()
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(
                path,
                json={"phone": "+2127000000", "password": "invalid", "legal_acknowledged": True},
            )
        else:
            raise ValueError(f"Unsupported method: {method}")
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        latencies.append(elapsed_ms)
        status_counts[res.status_code] = status_counts.get(res.status_code, 0) + 1

    failures = sum(v for k, v in status_counts.items() if k >= 500)
    return {
        "name": name,
        "count": count,
        "p50_ms": round(percentile(latencies, 50), 2),
        "p95_ms": round(percentile(latencies, 95), 2),
        "p99_ms": round(percentile(latencies, 99), 2),
        "avg_ms": round(statistics.mean(latencies), 2),
        "error_rate_5xx": round((failures / count) * 100.0, 2),
        "status_counts": status_counts,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    db_path = root / "codex_perf_baseline.db"
    os.environ["TEST_DB_PATH"] = str(db_path)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["DB_FALLBACK_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["APP_ENV"] = "development"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    from app.db.base import Base
    from app.db.session import engine
    from app.models.booking import Booking  # noqa: F401
    from app.models.booking_event import BookingEvent  # noqa: F401
    from app.models.booking_message import BookingMessage  # noqa: F401
    from app.models.market_item import FarmerMarketItem  # noqa: F401
    from app.models.market_order import MarketOrder  # noqa: F401
    from app.models.market_order_message import MarketOrderMessage  # noqa: F401
    from app.models.olive_inventory_item import FarmerOliveInventoryItem  # noqa: F401
    from app.models.olive_labor_day import FarmerOliveLaborDay  # noqa: F401
    from app.models.olive_land_piece import FarmerOliveLandPiece  # noqa: F401
    from app.models.olive_piece_metric import FarmerOlivePieceMetric  # noqa: F401
    from app.models.olive_sale import FarmerOliveSale  # noqa: F401
    from app.models.olive_season import FarmerOliveSeason  # noqa: F401
    from app.models.olive_usage import FarmerOliveUsage  # noqa: F401
    from app.models.user import User  # noqa: F401
    from app.models.worker import Worker  # noqa: F401
    from app.models.worker_availability_slot import WorkerAvailabilitySlot  # noqa: F401
    from app.main import app

    Base.metadata.create_all(bind=engine)

    client = TestClient(app)
    try:
        cases = [
            ("health", "GET", "/health"),
            ("workers_list", "GET", "/workers"),
            ("workers_filtered", "GET", "/workers?available=true&village=Sfax&work_date=2026-05-01&work_slot=full_day"),
            ("auth_login_invalid", "POST", "/auth/login"),
        ]

        print("Phase 0 local baseline (single-process TestClient, not network load):")
        for name, method, path in cases:
            result = run_case(client, name, method, path, count=200)
            print(result)
    finally:
        client.close()
        engine.dispose()
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass


if __name__ == "__main__":
    main()
