from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes_auth import router as auth_router
from app.api.routes_workers import router as workers_router
from app.db.base import Base
from app.db.session import engine
from app.models.booking import Booking
from app.models.booking_event import BookingEvent
from app.models.booking_message import BookingMessage
from app.models.user import User
from app.models.worker import Worker


def _ensure_schema_updates() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("workers"):
        return

    columns = {col["name"] for col in inspector.get_columns("workers")}
    if "available_days" not in columns:
        default_days = ",monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE workers "
                    "ADD COLUMN available_days VARCHAR(120) NOT NULL "
                    f"DEFAULT '{default_days}'"
                )
            )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Worker Radar API",
        description="MVP API for worker registration, search, and availability updates.",
        version="0.1.0",
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

    Base.metadata.create_all(bind=engine)
    _ensure_schema_updates()

    app.include_router(auth_router)
    app.include_router(workers_router)
    return app


app = create_app()
