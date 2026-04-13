from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes_auth import router as auth_router
from app.api.routes_workers import router as workers_router
from app.api.routes_olive_seasons import router as olive_seasons_router
from app.api.routes_olive_piece_metrics import router as olive_piece_metrics_router
from app.api.routes_olive_labor_days import router as olive_labor_days_router
from app.api.routes_olive_sales import router as olive_sales_router
from app.api.routes_olive_usages import router as olive_usages_router
from app.api.routes_olive_inventory_items import router as olive_inventory_items_router
from app.api.routes_olive_land_pieces import router as olive_land_pieces_router
from app.api.routes_market import router as market_router
from app.api.routes_agro_copilot import router as agro_copilot_router
from app.api.routes_uploads import router as uploads_router
from app.db.session import engine


def _ensure_market_order_review_columns_for_sqlite() -> None:
    # Safety net for local SQLite dev environments where migrations may have
    # been applied against a different relative DB file.
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "market_orders" not in table_names:
        return

    columns = {col["name"] for col in inspector.get_columns("market_orders")}
    add_columns_sql: list[str] = []

    if "market_rating" not in columns:
        add_columns_sql.append("ALTER TABLE market_orders ADD COLUMN market_rating INTEGER")
    if "market_review" not in columns:
        add_columns_sql.append("ALTER TABLE market_orders ADD COLUMN market_review VARCHAR(800)")
    if "market_reviewed_at" not in columns:
        add_columns_sql.append("ALTER TABLE market_orders ADD COLUMN market_reviewed_at DATETIME")

    if not add_columns_sql:
        return

    with engine.begin() as conn:
        for sql in add_columns_sql:
            conn.execute(text(sql))


def _ensure_worker_slot_schema_for_sqlite() -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "bookings" in table_names:
        columns = {col["name"] for col in inspector.get_columns("bookings")}
        if "work_slot" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN work_slot VARCHAR(20)"))
                conn.execute(
                    text(
                        "UPDATE bookings SET work_slot = 'full_day' "
                        "WHERE work_slot IS NULL OR work_slot = ''"
                    )
                )

    if "worker_availability_slots" not in table_names:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE worker_availability_slots (
                        id CHAR(32) NOT NULL PRIMARY KEY,
                        worker_id CHAR(32) NOT NULL,
                        work_date DATE NOT NULL,
                        slot_type VARCHAR(20) NOT NULL,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(worker_id) REFERENCES workers (id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_worker_availability_slots_worker_date "
                    "ON worker_availability_slots (worker_id, work_date)"
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX ux_worker_availability_slots_worker_date_slot "
                    "ON worker_availability_slots (worker_id, work_date, slot_type)"
                )
            )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ensure_market_order_review_columns_for_sqlite()
    _ensure_worker_slot_schema_for_sqlite()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Worker Radar API",
        description="MVP API for worker registration, search, and availability updates.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(workers_router)
    app.include_router(olive_seasons_router)
    app.include_router(olive_piece_metrics_router)
    app.include_router(olive_labor_days_router)
    app.include_router(olive_sales_router)
    app.include_router(olive_usages_router)
    app.include_router(olive_inventory_items_router)
    app.include_router(olive_land_pieces_router)
    app.include_router(market_router)
    app.include_router(agro_copilot_router)
    app.include_router(uploads_router)
    return app


app = create_app()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
